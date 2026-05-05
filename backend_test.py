"""GoalPilot AI Backend Tests — focus on the 3 current_focus tasks:

1. Idempotency-Key support on POST /api/goals (X-Idempotency-Key header)
2. APScheduler daily push job — verify wired (do NOT trigger)
3. Backend modular refactor — full smoke regression on all main endpoints
"""
import json
import os
import re
import subprocess
import time
import uuid
import asyncio
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
ENV_FILE = Path("/app/frontend/.env")
BACKEND_URL = None
for line in ENV_FILE.read_text().splitlines():
    if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
        BACKEND_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
assert BACKEND_URL, "EXPO_PUBLIC_BACKEND_URL not set"
API = f"{BACKEND_URL}/api"
print(f"Testing backend at: {API}\n")

results = {"passed": [], "failed": [], "warnings": []}


def ok(name, msg=""):
    results["passed"].append(name)
    print(f"  PASS  {name}{(' — ' + msg) if msg else ''}")


def fail(name, msg):
    results["failed"].append((name, msg))
    print(f"  FAIL  {name} — {msg}")


def warn(name, msg):
    results["warnings"].append((name, msg))
    print(f"  WARN  {name} — {msg}")


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Section 1 — Smoke regression with fresh user (covers refactor)
# ---------------------------------------------------------------------------
print("=" * 72)
print("SECTION 1 — Smoke regression (modular refactor)")
print("=" * 72)

uniq = uuid.uuid4().hex[:10]
SMOKE_EMAIL = f"smoke_{uniq}@goalpilot.ai"
SMOKE_PASSWORD = "Smoke@2026!"
SMOKE_NAME = f"Smoke User {uniq[:4]}"

# 1.1 register
r = requests.post(f"{API}/auth/register", json={
    "email": SMOKE_EMAIL,
    "password": SMOKE_PASSWORD,
    "name": SMOKE_NAME,
})
if r.status_code == 200 and r.json().get("token"):
    smoke_token = r.json()["token"]
    smoke_user = r.json()["user"]
    ok("POST /api/auth/register", f"user_id={smoke_user['id'][:8]}")
else:
    fail("POST /api/auth/register", f"{r.status_code} {r.text[:300]}")
    raise SystemExit("Register failed — cannot continue regression")

# 1.2 login
r = requests.post(f"{API}/auth/login", json={"email": SMOKE_EMAIL, "password": SMOKE_PASSWORD})
if r.status_code == 200 and r.json().get("token"):
    smoke_token = r.json()["token"]  # use latest
    ok("POST /api/auth/login", "token returned")
else:
    fail("POST /api/auth/login", f"{r.status_code} {r.text[:300]}")

# 1.3 me
r = requests.get(f"{API}/auth/me", headers=hdr(smoke_token))
if r.status_code == 200 and r.json().get("email") == SMOKE_EMAIL:
    ok("GET /api/auth/me", f"plan={r.json().get('plan')}")
else:
    fail("GET /api/auth/me", f"{r.status_code} {r.text[:200]}")

# 1.4 set locale
r = requests.post(f"{API}/auth/locale", json={"locale": "es"}, headers=hdr(smoke_token))
if r.status_code == 200 and r.json().get("locale") == "es":
    ok("POST /api/auth/locale", "locale=es persisted")
else:
    fail("POST /api/auth/locale", f"{r.status_code} {r.text[:200]}")

# 1.5 create goal — should return plan
goal_payload = {
    "title": "Aprender fotograf\u00eda b\u00e1sica",
    "deadline": "2026-12-31",
    "motivation": "Capturar momentos en familia con calidad profesional",
    "current_level": "beginner",
    "hours_per_week": 4,
}
r = requests.post(f"{API}/goals", json=goal_payload, headers=hdr(smoke_token))
goal_id = None
if r.status_code == 200:
    body = r.json()
    goal_id = body.get("id")
    if goal_id and isinstance(body.get("plan"), dict):
        ok("POST /api/goals", f"id={goal_id[:8]} plan_keys={list(body['plan'].keys())}")
    else:
        fail("POST /api/goals", f"missing id or plan: {json.dumps(body)[:300]}")
else:
    fail("POST /api/goals", f"{r.status_code} {r.text[:300]}")

# 1.6 list goals
r = requests.get(f"{API}/goals", headers=hdr(smoke_token))
if r.status_code == 200 and isinstance(r.json(), list):
    ok("GET /api/goals", f"count={len(r.json())}")
else:
    fail("GET /api/goals", f"{r.status_code} {r.text[:200]}")

# 1.7 get goal by id
if goal_id:
    r = requests.get(f"{API}/goals/{goal_id}", headers=hdr(smoke_token))
    if r.status_code == 200 and r.json().get("id") == goal_id:
        ok("GET /api/goals/{id}", "match")
    else:
        fail("GET /api/goals/{id}", f"{r.status_code} {r.text[:200]}")

# 1.8 list tasks
r = requests.get(f"{API}/tasks", headers=hdr(smoke_token))
tasks = []
if r.status_code == 200 and isinstance(r.json(), list):
    tasks = r.json()
    ok("GET /api/tasks", f"count={len(tasks)}")
else:
    fail("GET /api/tasks", f"{r.status_code} {r.text[:200]}")

# 1.9 patch a task -> completed:true
if tasks:
    t0_id = tasks[0]["id"]
    r = requests.patch(f"{API}/tasks/{t0_id}", json={"completed": True}, headers=hdr(smoke_token))
    if r.status_code == 200 and r.json().get("completed") is True:
        ok("PATCH /api/tasks/{id}", "completed=true")
    else:
        fail("PATCH /api/tasks/{id}", f"{r.status_code} {r.text[:200]}")
else:
    warn("PATCH /api/tasks/{id}", "no tasks to patch (AI plan may have produced none)")

# 1.10 missed
r = requests.get(f"{API}/tasks/missed", headers=hdr(smoke_token))
if r.status_code == 200 and isinstance(r.json(), list):
    ok("GET /api/tasks/missed", f"count={len(r.json())}")
else:
    fail("GET /api/tasks/missed", f"{r.status_code} {r.text[:200]}")

# 1.11 dashboard stats
r = requests.get(f"{API}/dashboard/stats", headers=hdr(smoke_token))
if r.status_code == 200:
    j = r.json()
    if all(k in j for k in ("streak", "active_goals", "today_total", "today_done")):
        ok("GET /api/dashboard/stats",
           f"streak={j['streak']} active_goals={j['active_goals']} today_done={j['today_done']}/{j['today_total']}")
    else:
        fail("GET /api/dashboard/stats", f"missing keys: {j}")
else:
    fail("GET /api/dashboard/stats", f"{r.status_code} {r.text[:200]}")

# 1.12 nudge
r = requests.get(f"{API}/nudge", headers=hdr(smoke_token))
if r.status_code == 200 and "show" in r.json():
    ok("GET /api/nudge", f"show={r.json().get('show')}")
else:
    fail("GET /api/nudge", f"{r.status_code} {r.text[:200]}")

# 1.13 weekly review
r = requests.get(f"{API}/review/weekly", headers=hdr(smoke_token))
if r.status_code == 200:
    j = r.json()
    if "summary" in j and "completion_rate" in j:
        ok("GET /api/review/weekly",
           f"completion_rate={j['completion_rate']}% summary_len={len(j['summary'] or '')}")
    else:
        fail("GET /api/review/weekly", f"missing keys: {j}")
else:
    fail("GET /api/review/weekly", f"{r.status_code} {r.text[:300]}")

# 1.14 calendar url -> token
r = requests.get(f"{API}/calendar/url", headers=hdr(smoke_token))
cal_token = None
if r.status_code == 200 and r.json().get("token"):
    cal_token = r.json()["token"]
    ok("GET /api/calendar/url", "token returned")
else:
    fail("GET /api/calendar/url", f"{r.status_code} {r.text[:200]}")

# 1.15 calendar export.ics
if cal_token:
    r = requests.get(f"{API}/calendar/export.ics", params={"token": cal_token})
    ct = r.headers.get("content-type", "")
    body = r.text or ""
    if r.status_code == 200 and ("text/calendar" in ct or "BEGIN:VCALENDAR" in body):
        ok("GET /api/calendar/export.ics", f"ct={ct} bytes={len(body)}")
    else:
        fail("GET /api/calendar/export.ics", f"{r.status_code} ct={ct} body[:120]={body[:120]}")

# 1.16 checkout/session
r = requests.post(
    f"{API}/checkout/session",
    json={"package_id": "pro_monthly", "origin_url": "https://example.com"},
    headers=hdr(smoke_token),
)
if r.status_code == 200:
    j = r.json()
    if j.get("url") and j.get("session_id"):
        ok("POST /api/checkout/session", f"session_id={j['session_id'][:14]}")
    else:
        fail("POST /api/checkout/session", f"missing fields: {j}")
else:
    # Stripe test key may fail externally; treat 5xx as warning, but spec wants 200
    fail("POST /api/checkout/session", f"{r.status_code} {r.text[:300]}")

# 1.17 webhook bad signature -> 400
r = requests.post(
    f"{API}/webhook/stripe",
    data=b"{}",
    headers={"Stripe-Signature": "bad", "Content-Type": "application/json"},
)
if r.status_code == 400:
    ok("POST /api/webhook/stripe (bad sig)", "400 as expected")
else:
    fail("POST /api/webhook/stripe (bad sig)", f"{r.status_code} {r.text[:200]}")

# 1.18 delete goal
if goal_id:
    r = requests.delete(f"{API}/goals/{goal_id}", headers=hdr(smoke_token))
    if r.status_code == 200 and r.json().get("ok") is True:
        ok("DELETE /api/goals/{id}", "deleted")
    else:
        fail("DELETE /api/goals/{id}", f"{r.status_code} {r.text[:200]}")

# ---------------------------------------------------------------------------
# Section 2 — Idempotency-Key on POST /api/goals
# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("SECTION 2 — Idempotency-Key on POST /api/goals")
print("=" * 72)

# Use fresh user to avoid cross-test pollution
uniq2 = uuid.uuid4().hex[:10]
IDEM_EMAIL = f"idem_{uniq2}@goalpilot.ai"
r = requests.post(f"{API}/auth/register", json={
    "email": IDEM_EMAIL, "password": "Idem@2026!", "name": f"Idem {uniq2[:4]}"
})
assert r.status_code == 200, f"idem register failed: {r.status_code} {r.text}"
idem_token = r.json()["token"]
idem_user_id = r.json()["user"]["id"]
print(f"  fresh user: {IDEM_EMAIL} id={idem_user_id[:8]}")

idem_payload = {
    "title": "Run a 5K in under 30 minutes",
    "deadline": "2026-09-15",
    "motivation": "Improve cardiovascular fitness for energy and longevity",
    "current_level": "beginner",
    "hours_per_week": 3,
}

# 2.1 First request with key K1 -> 200
K1 = str(uuid.uuid4())
r1 = requests.post(
    f"{API}/goals",
    json=idem_payload,
    headers={**hdr(idem_token), "X-Idempotency-Key": K1},
)
if r1.status_code == 200:
    g1 = r1.json()
    g1_id = g1.get("id")
    ok("Idem 200 — first call with key", f"goal id={g1_id[:8]}")
else:
    fail("Idem 200 — first call with key", f"{r1.status_code} {r1.text[:300]}")
    g1_id = None

# 2.2 Same body + same key K1 -> replay, same goal id, status 200
r2 = requests.post(
    f"{API}/goals",
    json=idem_payload,
    headers={**hdr(idem_token), "X-Idempotency-Key": K1},
)
if r2.status_code == 200 and g1_id and r2.json().get("id") == g1_id:
    ok("Idem 200 replay", f"same goal id={g1_id[:8]}")
else:
    fail("Idem 200 replay",
         f"status={r2.status_code} replay_id={r2.json().get('id') if r2.headers.get('content-type','').startswith('application/json') else r2.text[:120]} expected={g1_id}")

# 2.3 Verify cache row in idempotency_keys
async def _check_cache_row(user_id, key, expected_status):
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo = AsyncIOMotorClient("mongodb://localhost:27017")
    db = mongo["goalpilot_db"]
    doc = await db.idempotency_keys.find_one({"user_id": user_id, "key": key})
    mongo.close()
    return doc

doc = asyncio.run(_check_cache_row(idem_user_id, K1, 200))
if doc and doc.get("status_code") == 200 and doc.get("created_at"):
    ok("idempotency_keys cache (200 row)",
       f"keys={sorted(set(doc.keys()) & {'user_id','key','status_code','response','created_at'})}")
else:
    fail("idempotency_keys cache (200 row)", f"doc={doc}")

# 2.4 No-key second call should hit free-plan cap (402)
r3 = requests.post(f"{API}/goals", json=idem_payload, headers=hdr(idem_token))
if r3.status_code == 402:
    ok("No-key 402 (free plan cap)", f"detail={r3.json().get('detail','')[:80]}")
else:
    fail("No-key 402 (free plan cap)", f"{r3.status_code} {r3.text[:200]}")

# 2.5 Idempotent 402: hit cap with new key K2, then retry K2 -> still 402
K2 = str(uuid.uuid4())
r4 = requests.post(
    f"{API}/goals",
    json=idem_payload,
    headers={**hdr(idem_token), "X-Idempotency-Key": K2},
)
if r4.status_code == 402:
    ok("Idem 402 — first cap-hit with key", f"detail={r4.json().get('detail','')[:60]}")
else:
    fail("Idem 402 — first cap-hit with key", f"{r4.status_code} {r4.text[:200]}")

r5 = requests.post(
    f"{API}/goals",
    json=idem_payload,
    headers={**hdr(idem_token), "X-Idempotency-Key": K2},
)
if r5.status_code == 402:
    ok("Idem 402 replay", f"still 402 on retry with K2")
else:
    fail("Idem 402 replay", f"{r5.status_code} {r5.text[:200]}")

# 2.6 Verify 402 cache row
doc402 = asyncio.run(_check_cache_row(idem_user_id, K2, 402))
if doc402 and doc402.get("status_code") == 402 and doc402.get("detail"):
    ok("idempotency_keys cache (402 row)",
       f"detail={doc402.get('detail','')[:50]} created_at={doc402.get('created_at','')[:19]}")
else:
    fail("idempotency_keys cache (402 row)", f"doc={doc402}")

# ---------------------------------------------------------------------------
# Section 3 — APScheduler daily push job (verify only)
# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("SECTION 3 — APScheduler daily push job (verify wiring; DO NOT trigger)")
print("=" * 72)

try:
    out = subprocess.run(
        ["grep", "-c", "Scheduler started: daily push at 09:00 UTC", "/var/log/supervisor/backend.err.log"],
        capture_output=True, text=True, check=False,
    )
    count = int((out.stdout or "0").strip() or "0")
    if count >= 1:
        ok("Scheduler log line present", f"matches={count}")
    else:
        fail("Scheduler log line present", "not found in backend.err.log")
except Exception as e:
    fail("Scheduler log grep", str(e))

# Sanity: API root still serves
r = requests.get(f"{API}/")
if r.status_code == 200 and r.json().get("status") == "ok":
    ok("API root /api/ still serves", "scheduler did not break startup")
else:
    fail("API root /api/", f"{r.status_code} {r.text[:200]}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print(f"PASSED: {len(results['passed'])}")
print(f"FAILED: {len(results['failed'])}")
print(f"WARN  : {len(results['warnings'])}")
if results["failed"]:
    print("\nFAILURES:")
    for n, m in results["failed"]:
        print(f"  - {n}: {m}")
if results["warnings"]:
    print("\nWARNINGS:")
    for n, m in results["warnings"]:
        print(f"  - {n}: {m}")
print("=" * 72)
exit(1 if results["failed"] else 0)
