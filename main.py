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

# Endpoint 1: Issue Token (Called by ESP32 / Reception / Kiosk)
@app.post("/tokens/issue")
async def issue_token(priority: str = "general"):
    priority_clean = priority.lower().strip()
    is_emergency = priority_clean in ("emergency", "critical", "urgent")
    is_priority = priority_clean in ("priority", "senior", "true")

    if is_emergency:
        token_num = await r.incr("opd:token_counter:emergency")
        token_id = f"E-{token_num:03d}"
        await r.rpush("opd:queue:emergency", token_id)
        effective_priority = "emergency"
    elif is_priority:
        token_num = await r.incr("opd:token_counter")
        token_id = f"T-{token_num:03d}"
        await r.rpush("opd:queue:priority", token_id)
        effective_priority = "priority"
    else:
        token_num = await r.incr("opd:token_counter")
        token_id = f"T-{token_num:03d}"
        await r.rpush("opd:queue:general", token_id)
        effective_priority = "general"

    emergency_len = await r.llen("opd:queue:emergency")
    priority_len = await r.llen("opd:queue:priority")
    general_len = await r.llen("opd:queue:general")

    if is_emergency:
        queue_position = emergency_len
        estimated_wait = "Immediate / 0 mins"
    elif is_priority:
        queue_position = emergency_len + priority_len
        estimated_wait = f"{queue_position * 5} mins"
    else:
        queue_position = emergency_len + priority_len + general_len
        estimated_wait = f"{queue_position * 5} mins"

    token_data = {
        "token_id": token_id,
        "priority": effective_priority,
        "status": "WAITING",
        "queue_position": str(queue_position),
        "estimated_wait": estimated_wait
    }

    await r.hset(f"token:{token_id}", mapping=token_data)

    await manager.broadcast(json.dumps({
        "event": "TOKEN_ISSUED",
        "token": token_data
    }))

    return token_data

async def complete_active_token_on_counter(counter_id: int):
    active_key = f"opd:counter:{counter_id}:active"
    prev_token_id = await r.get(active_key)
    if prev_token_id:
        current_status = await r.hget(f"token:{prev_token_id}", "status")
        prev_priority = await r.hget(f"token:{prev_token_id}", "priority")
        was_emergency = (prev_priority == "emergency" or prev_token_id.startswith("E-"))

        if current_status == "CALLED":
            await r.hset(f"token:{prev_token_id}", "status", "COMPLETED")
            if was_emergency:
                await r.delete("opd:emergency_active")

            await manager.broadcast(json.dumps({
                "event": "TOKEN_COMPLETED",
                "token_id": prev_token_id,
                "counter_id": counter_id,
                "was_emergency": was_emergency
            }))
        await r.delete(active_key)

# Endpoint 2: Call Next Token (Called by Doctor Console)
@app.post("/tokens/next")
async def call_next_token(counter_id: int):
    # Complete previous patient first
    await complete_active_token_on_counter(counter_id)

    # Precedence: Emergency -> Priority -> General
    token_id = await r.lpop("opd:queue:emergency")
    if not token_id:
        token_id = await r.lpop("opd:queue:priority")
    if not token_id:
        token_id = await r.lpop("opd:queue:general")

    if not token_id:
        raise HTTPException(status_code=404, detail="No patients waiting in queue.")

    token_priority = await r.hget(f"token:{token_id}", "priority")
    is_emergency = (token_priority == "emergency" or token_id.startswith("E-"))

    await r.hset(f"token:{token_id}", mapping={
        "status": "CALLED",
        "counter_id": str(counter_id)
    })

    # Save the currently active token for this counter
    await r.set(f"opd:counter:{counter_id}:active", token_id)
    if is_emergency:
        await r.set("opd:emergency_active", token_id)
    else:
        # Check if this counter was holding emergency; if not, clear emergency active if it was this token
        curr_emerg = await r.get("opd:emergency_active")
        if curr_emerg == token_id:
            await r.delete("opd:emergency_active")

    payload = {
        "event": "TOKEN_CALLED",
        "token_id": token_id,
        "counter_id": counter_id,
        "priority": token_priority or ("emergency" if is_emergency else "general"),
        "is_emergency": is_emergency,
        "delay_minutes": 8 if is_emergency else 0
    }

    await manager.broadcast(json.dumps(payload))
    return {"status": "success", "data": payload}

# Endpoint 2B: Call Emergency Token (Called by Doctor Console)
@app.post("/tokens/call_emergency")
async def call_emergency_token(counter_id: int):
    # Check if there is an existing emergency waiting in queue
    token_id = await r.lpop("opd:queue:emergency")
    if not token_id:
        raise HTTPException(status_code=404, detail="No emergency patients waiting in queue.")

    # Complete previous patient first only when emergency token exists
    await complete_active_token_on_counter(counter_id)

    token_priority = await r.hget(f"token:{token_id}", "priority")

    await r.hset(f"token:{token_id}", mapping={
        "status": "CALLED",
        "counter_id": str(counter_id)
    })

    await r.set(f"opd:counter:{counter_id}:active", token_id)
    await r.set("opd:emergency_active", token_id)

    payload = {
        "event": "TOKEN_CALLED",
        "token_id": token_id,
        "counter_id": counter_id,
        "priority": token_priority or "emergency",
        "is_emergency": True,
        "delay_minutes": 8
    }

    await manager.broadcast(json.dumps(payload))
    return {"status": "success", "data": payload}

# Endpoint 5: Complete Token (Called by Doctor Console or automatically)
@app.post("/tokens/complete")
async def complete_token(token_id: str, counter_id: int):
    # Verify token exists
    token_exists = await r.exists(f"token:{token_id}")
    if not token_exists:
        raise HTTPException(status_code=404, detail=f"Token {token_id} not found.")

    token_priority = await r.hget(f"token:{token_id}", "priority")
    was_emergency = (token_priority == "emergency" or token_id.startswith("E-"))

    await r.hset(f"token:{token_id}", "status", "COMPLETED")

    # Clear active status for this counter if it matches
    active_key = f"opd:counter:{counter_id}:active"
    prev_token_id = await r.get(active_key)
    if prev_token_id == token_id:
        await r.delete(active_key)

    if was_emergency:
        await r.delete("opd:emergency_active")

    payload = {
        "event": "TOKEN_COMPLETED",
        "token_id": token_id,
        "counter_id": counter_id,
        "was_emergency": was_emergency
    }

    await manager.broadcast(json.dumps(payload))
    return {"status": "success", "data": payload}

# Endpoint 4: Recall Token (Called by Doctor Console)
@app.post("/tokens/recall")
async def recall_token(token_id: str, counter_id: int):
    # Verify token exists
    token_exists = await r.exists(f"token:{token_id}")
    if not token_exists:
        raise HTTPException(status_code=404, detail=f"Token {token_id} not found.")

    token_priority = await r.hget(f"token:{token_id}", "priority")
    is_emergency = (token_priority == "emergency" or token_id.startswith("E-"))

    # Complete the previously active token if it's different from the recalled one
    active_key = f"opd:counter:{counter_id}:active"
    prev_token_id = await r.get(active_key)
    if prev_token_id and prev_token_id != token_id:
        await complete_active_token_on_counter(counter_id)

    await r.hset(f"token:{token_id}", mapping={
        "status": "CALLED",
        "counter_id": str(counter_id)
    })

    await r.set(active_key, token_id)
    if is_emergency:
        await r.set("opd:emergency_active", token_id)

    payload = {
        "event": "TOKEN_CALLED",
        "token_id": token_id,
        "counter_id": counter_id,
        "priority": token_priority or ("emergency" if is_emergency else "general"),
        "is_emergency": is_emergency,
        "delay_minutes": 8 if is_emergency else 0
    }

    await manager.broadcast(json.dumps(payload))
    return {"status": "success", "data": payload}

# Endpoint 6: Current Emergency Status
@app.get("/tokens/emergency_status")
async def get_emergency_status():
    active_emerg = await r.get("opd:emergency_active")
    emerg_queue_len = await r.llen("opd:queue:emergency")
    return {
        "is_emergency_active": bool(active_emerg),
        "active_token_id": active_emerg,
        "waiting_emergency_count": emerg_queue_len,
        "delay_minutes": 8 if active_emerg else 0
    }


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