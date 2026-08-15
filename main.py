import json
import os
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import redis.asyncio as redis


app = FastAPI(title="Clinic OPD Queue Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# Connect to Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.from_url(redis_url, decode_responses=True)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
                await connection.send_text(message)

manager = ConnectionManager()

# Endpoint 1: Issue Token (Called by ESP32 / Reception)
@app.post("/tokens/issue")
async def issue_token(priority: str = "general"):
    token_num = await r.incr("opd:token_counter")
    token_id = f"T-{token_num:03d}"
    
    if priority.lower() in ("priority", "true"):
        await r.rpush("opd:queue:priority", token_id)
    else:
        await r.rpush("opd:queue:general", token_id)

    priority_len = await r.llen("opd:queue:priority")
    general_len = await r.llen("opd:queue:general")

    if priority.lower() in ("priority", "true"):
        queue_position = priority_len
    else:
        queue_position = priority_len + general_len

    token_data = {
        "token_id": token_id,
        "priority": priority,
        "status": "WAITING",
        "queue_position": queue_position,
        "estimated_wait": f"{queue_position * 5} mins"
    }

    await r.hset(f"token:{token_id}", mapping=token_data)

    await manager.broadcast(json.dumps({
        "event": "TOKEN_ISSUED",
        "token": token_data
    }))

    return token_data

# Endpoint 2: Call Next Token (Called by Doctor Console)
@app.post("/tokens/next")
async def call_next_token(counter_id: int):
    # Try popping from priority queue first, fallback to general
    token_id = await r.lpop("opd:queue:priority")
    if not token_id:
        token_id = await r.lpop("opd:queue:general")

    if not token_id:
        raise HTTPException(status_code=404, detail="No patients waiting in queue.")

    await r.hset(f"token:{token_id}", mapping={
        "status": "CALLED",
        "counter_id": str(counter_id)
    }
)

    payload = {
        "event": "TOKEN_CALLED",
        "token_id": token_id,
        "counter_id": counter_id
    }

    await manager.broadcast(json.dumps(payload))
    return {"status":"success","data":payload}

# Endpoint 4: Recall Token (Called by Doctor Console)
@app.post("/tokens/recall")
async def recall_token(token_id: str, counter_id: int):
    # Verify token exists
    token_exists = await r.exists(f"token:{token_id}")
    if not token_exists:
        raise HTTPException(status_code=404, detail=f"Token {token_id} not found.")

    await r.hset(f"token:{token_id}", mapping={
        "status": "CALLED",
        "counter_id": str(counter_id)
    })

    payload = {
        "event": "TOKEN_CALLED",
        "token_id": token_id,
        "counter_id": counter_id
    }

    await manager.broadcast(json.dumps(payload))
    return {"status": "success", "data": payload}

# Endpoint 3: Real-time WebSocket (Connected by Display Board)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data =await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)