"""Section 3 retest — AI plan generation (after max_tokens=16000 + AT MOST 12 prompt cap).

Live preview backend.
"""
import json
import sys
import time
import uuid
from datetime import date, timedelta

import requests

BASE = "https://goal-pilot-ai.preview.emergentagent.com/api"
TIMEOUT = 180  # AI calls can be slow

results = []


def log(name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}  {detail}")
    results.append((name, ok, detail))


def register_fresh():
    email = f"sect3_{uuid.uuid4().hex[:10]}@goalpilot.ai"
    password = "Test@1234"
    name = "Section3 Tester"
    r = requests.post(f"{BASE}/auth/register",
                      json={"email": email, "password": password, "name": name},
                      timeout=30)
    assert r.status_code == 200, f"register: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("token") or body.get("access_token")
    if not token:
        raise AssertionError(f"no token in register response: {body}")
    return token, email


def auth_h(token):
    return {"Authorization": f"Bearer {token}"}


def test1_long_horizon():
    print("\n=== Test 1: long-horizon B1 Spanish goal ===")
    token, email = register_fresh()
    print(f"User: {email}")
    payload = {
        "title": "Learn Spanish to B1 level",
        "deadline": "2026-12-31",
        "motivation": "Travel in Spain",
        "current_level": "beginner",
        "hours_per_week": 5,
    }
    t0 = time.time()
    r = requests.post(f"{BASE}/goals", json=payload, headers=auth_h(token), timeout=TIMEOUT)
    dt = time.time() - t0
    print(f"POST /api/goals -> {r.status_code} in {dt:.1f}s")
    if r.status_code != 200:
        log("T1 POST /api/goals returns 200", False, f"status={r.status_code} body={r.text[:300]}")
        return None, None
    log("T1 POST /api/goals returns 200", True, f"({dt:.1f}s)")
    g = r.json()
    plan = g.get("plan") or {}
    milestones = plan.get("milestones") or []
    weekly_plan = plan.get("weekly_plan") or []
    daily_tasks = plan.get("daily_tasks") or []
    summary = plan.get("summary") or ""
    print(f"  milestones={len(milestones)} weekly_plan={len(weekly_plan)} daily_tasks={len(daily_tasks)} summary_len={len(summary)}")

    log("T1 milestones >= 3", len(milestones) >= 3, f"got {len(milestones)}")
    log("T1 weekly_plan 1..12", 1 <= len(weekly_plan) <= 12, f"got {len(weekly_plan)}")
    log("T1 daily_tasks >= 5", len(daily_tasks) >= 5, f"got {len(daily_tasks)}")
    log("T1 summary > 50 chars", len(summary) > 50, f"got {len(summary)}")
    return token, g


def test2_tasks_count(token, goal):
    print("\n=== Test 2: GET /api/tasks count == daily_tasks length ===")
    if not token or not goal:
        log("T2 GET /api/tasks", False, "skipped (T1 failed)")
        return
    expected = len(goal["plan"].get("daily_tasks") or [])
    r = requests.get(f"{BASE}/tasks", headers=auth_h(token), timeout=30)
    if r.status_code != 200:
        log("T2 GET /api/tasks 200", False, f"status={r.status_code}")
        return
    tasks = r.json()
    # Filter by goal_id to be safe
    goal_tasks = [t for t in tasks if t.get("goal_id") == goal["id"]]
    print(f"  tasks={len(tasks)} goal-scoped={len(goal_tasks)} expected={expected}")
    log("T2 tasks count matches daily_tasks", len(goal_tasks) == expected,
        f"got {len(goal_tasks)} expected {expected}")


def test3_replan(token, goal):
    print("\n=== Test 3: POST /api/goals/{id}/replan deadline 2027-06-30 ===")
    if not token or not goal:
        log("T3 replan", False, "skipped (T1 failed)")
        return
    t0 = time.time()
    r = requests.post(
        f"{BASE}/goals/{goal['id']}/replan",
        json={"deadline": "2027-06-30"},
        headers=auth_h(token),
        timeout=TIMEOUT,
    )
    dt = time.time() - t0
    print(f"POST replan -> {r.status_code} in {dt:.1f}s")
    if r.status_code != 200:
        log("T3 replan returns 200", False, f"status={r.status_code} body={r.text[:300]}")
        return
    log("T3 replan returns 200", True, f"({dt:.1f}s)")
    updated = r.json()
    plan = updated.get("plan") or {}
    milestones = plan.get("milestones") or []
    weekly_plan = plan.get("weekly_plan") or []
    print(f"  milestones={len(milestones)} weekly_plan={len(weekly_plan)} deadline={updated.get('deadline')}")
    log("T3 milestones non-empty", len(milestones) > 0, f"got {len(milestones)}")
    log("T3 weekly_plan 1..12", 1 <= len(weekly_plan) <= 12, f"got {len(weekly_plan)}")
    log("T3 deadline updated", updated.get("deadline") == "2027-06-30",
        f"got {updated.get('deadline')}")


def test4_short_horizon():
    print("\n=== Test 4: short-horizon goal (6 weeks) ===")
    token, email = register_fresh()
    print(f"User: {email}")
    deadline = (date.today() + timedelta(weeks=6)).isoformat()
    payload = {
        "title": "Build a daily journaling habit",
        "deadline": deadline,
        "motivation": "Mental clarity",
        "current_level": "beginner",
        "hours_per_week": 3,
    }
    t0 = time.time()
    r = requests.post(f"{BASE}/goals", json=payload, headers=auth_h(token), timeout=TIMEOUT)
    dt = time.time() - t0
    print(f"POST /api/goals -> {r.status_code} in {dt:.1f}s")
    if r.status_code != 200:
        log("T4 POST /api/goals 200", False, f"status={r.status_code} body={r.text[:300]}")
        return
    log("T4 POST /api/goals 200", True, f"({dt:.1f}s)")
    g = r.json()
    plan = g.get("plan") or {}
    weekly_plan = plan.get("weekly_plan") or []
    print(f"  weekly_plan={len(weekly_plan)} deadline={deadline}")
    log("T4 weekly_plan <= 6", len(weekly_plan) <= 6, f"got {len(weekly_plan)}")
    log("T4 weekly_plan >= 1", len(weekly_plan) >= 1, f"got {len(weekly_plan)}")


def main():
    print(f"Section 3 retest against {BASE}")
    token, goal = test1_long_horizon()
    test2_tasks_count(token, goal)
    test3_replan(token, goal)
    test4_short_horizon()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n========================================")
    print(f"RESULT: {passed}/{total} assertions passed")
    print(f"========================================")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAIL: {name} -- {detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
