import asyncio
import json
from main import (
    issue_token,
    call_next_token,
    call_emergency_token,
    complete_token,
    get_emergency_status,
    r
)

async def run_tests():
    print("Connecting to Redis and flushing test keys...")
    await r.flushdb()

    # 1. Issue general token
    t1 = await issue_token(priority="general")
    print(f"1. Issued general: {t1['token_id']}, priority: {t1['priority']}")
    assert t1["token_id"].startswith("T-")
    assert t1["priority"] == "general"

    # 2. Issue priority token
    t2 = await issue_token(priority="priority")
    print(f"2. Issued priority: {t2['token_id']}, priority: {t2['priority']}")
    assert t2["token_id"].startswith("T-")
    assert t2["priority"] == "priority"

    # 3. Issue emergency token
    t3 = await issue_token(priority="emergency")
    print(f"3. Issued emergency: {t3['token_id']}, priority: {t3['priority']}")
    assert t3["token_id"].startswith("E-")
    assert t3["priority"] == "emergency"

    # 4. Call next token at Counter 1: Emergency MUST be called first!
    res1 = await call_next_token(counter_id=1)
    call1 = res1["data"]
    print(f"4. First called: {call1['token_id']}, is_emergency: {call1['is_emergency']}, delay: {call1['delay_minutes']} mins")
    assert call1["token_id"] == t3["token_id"], f"Expected emergency {t3['token_id']}, got {call1['token_id']}"
    assert call1["is_emergency"] is True
    assert call1["delay_minutes"] == 8

    # 5. Check emergency status while active
    status1 = await get_emergency_status()
    print(f"5. Emergency status active: {status1}")
    assert status1["is_emergency_active"] is True
    assert status1["active_token_id"] == t3["token_id"]
    assert status1["delay_minutes"] == 8

    # 6. Complete emergency token
    res_comp = await complete_token(token_id=t3["token_id"], counter_id=1)
    comp = res_comp["data"]
    print(f"6. Completed token: {comp['token_id']}, was_emergency: {comp['was_emergency']}")
    assert comp["was_emergency"] is True

    # 7. Check emergency status after completion
    status2 = await get_emergency_status()
    print(f"7. Emergency status resolved: {status2}")
    assert status2["is_emergency_active"] is False

    # 8. Call next: Priority queue must be called next
    res2 = await call_next_token(counter_id=1)
    call2 = res2["data"]
    print(f"8. Second called: {call2['token_id']}, is_emergency: {call2['is_emergency']}")
    assert call2["token_id"] == t2["token_id"]
    assert call2["is_emergency"] is False

    # 9. Call next: General queue must be called third
    res3 = await call_next_token(counter_id=1)
    call3 = res3["data"]
    print(f"9. Third called: {call3['token_id']}, is_emergency: {call3['is_emergency']}")
    assert call3["token_id"] == t1["token_id"]
    assert call3["is_emergency"] is False

    # 10. Attempt to call emergency when emergency queue is empty (MUST fail with 404, NO auto-generation!)
    from fastapi import HTTPException
    empty_error_raised = False
    try:
        await call_emergency_token(counter_id=2)
    except HTTPException as e:
        empty_error_raised = True
        assert e.status_code == 404
        assert "No emergency patients waiting" in e.detail
        print(f"10. Empty emergency queue test PASSED: correctly raised 404 ({e.detail})")
    assert empty_error_raised, "Expected HTTPException 404 when emergency queue is empty, but no exception was raised!"

    # 11. Now explicitly issue an emergency token from kiosk/reception
    t4 = await issue_token(priority="emergency")
    print(f"11. Issued legitimate emergency token: {t4['token_id']}")
    assert t4["token_id"].startswith("E-")

    # 12. Calling emergency token now succeeds with the issued token
    res_emg = await call_emergency_token(counter_id=2)
    emg = res_emg["data"]
    print(f"12. Called waiting emergency token: {emg['token_id']}, is_emergency: {emg['is_emergency']}, delay: {emg['delay_minutes']}")
    assert emg["token_id"] == t4["token_id"]
    assert emg["is_emergency"] is True
    assert emg["delay_minutes"] == 8

    # 13. Calling emergency again immediately must fail with 404 since queue is empty again
    empty_again = False
    try:
        await call_emergency_token(counter_id=2)
    except HTTPException as e:
        empty_again = True
        assert e.status_code == 404
        print(f"13. Immediate second emergency call correctly rejected with 404: {e.detail}")
    assert empty_again, "Expected second call to fail with 404 since emergency queue should now be empty!"

    print("\n✅ ALL TESTS PASSED PERFECTLY - NO AUTO GENERATION OF EMERGENCY TOKENS!")

if __name__ == "__main__":
    asyncio.run(run_tests())
