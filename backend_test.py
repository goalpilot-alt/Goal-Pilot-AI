"""GoalPilot AI Backend Tests
Focus: /api/auth/locale, AI plan localization, /api/webhook/stripe, regression on core endpoints.
"""
import os
import sys
import json
import uuid
import time
import requests
from pathlib import Path

# Read backend URL from frontend/.env
ENV_FILE = Path("/app/frontend/.env")
BACKEND_URL = None
for line in ENV_FILE.read_text().splitlines():
    if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
        BACKEND_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

assert BACKEND_URL, "EXPO_PUBLIC_BACKEND_URL not set"
API = f"{BACKEND_URL}/api"
print(f"Testing backend at: {API}")

EMAIL = "tester@goalpilot.ai"
PASSWORD = "Test@1234"
NAME = "Tester"

results = {"passed": [], "failed": [], "warnings": []}


def record_pass(name, info=""):
    print(f"PASS: {name} {info}")
    results["passed"].append((name, info))


def record_fail(name, info=""):
    print(f"FAIL: {name} {info}")
    results["failed"].append((name, info))


def record_warn(name, info=""):
    print(f"WARN: {name} {info}")
    results["warnings"].append((name, info))


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Setup user ----------
def ensure_user():
    # Try login first
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code == 200:
        return r.json()
    # Else register
    r = requests.post(f"{API}/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": NAME}, timeout=30)
    if r.status_code == 200:
        return r.json()
    if r.status_code == 400 and "already" in r.text.lower():
        # password mismatch — just attempt login again
        r2 = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
        if r2.status_code == 200:
            return r2.json()
    raise RuntimeError(f"Could not auth: {r.status_code} {r.text}")


auth_data = ensure_user()
TOKEN = auth_data["token"]
USER = auth_data["user"]
USER_ID = USER["id"]
print(f"Authenticated as user_id={USER_ID}")


# =========================================================================
# 1. POST /api/auth/locale
# =========================================================================
def test_locale_happy_paths():
    locales = ["en-US", "en-GB", "es", "fr", "cs", "sk", "ru", "zh-CN"]
    all_ok = True
    for loc in locales:
        r = requests.post(f"{API}/auth/locale", headers=auth_headers(TOKEN), json={"locale": loc}, timeout=15)
        if r.status_code != 200:
            record_fail(f"locale[{loc}]", f"expected 200 got {r.status_code} body={r.text}")
            all_ok = False
            continue
        data = r.json()
        if not (data.get("ok") is True and data.get("locale") == loc):
            record_fail(f"locale[{loc}]", f"unexpected body {data}")
            all_ok = False
    if all_ok:
        record_pass("POST /api/auth/locale happy paths (8 locales)")
    return all_ok


def test_locale_unsupported():
    fails = 0
    for bad in ["xx", "de", ""]:
        r = requests.post(f"{API}/auth/locale", headers=auth_headers(TOKEN), json={"locale": bad}, timeout=15)
        if r.status_code != 400:
            record_fail(f"locale[{bad!r}] expected 400", f"got {r.status_code} body={r.text}")
            fails += 1
            continue
        if "Unsupported locale" not in r.text:
            record_warn(f"locale[{bad!r}] 400 detail mismatch", r.text)
    if fails == 0:
        record_pass("POST /api/auth/locale unsupported -> 400")
    return fails == 0


def test_locale_no_auth():
    r = requests.post(f"{API}/auth/locale", headers={"Content-Type": "application/json"}, json={"locale": "es"}, timeout=15)
    # FastAPI HTTPBearer with auto_error=False raises 401 manually
    if r.status_code in (401, 403):
        record_pass(f"POST /api/auth/locale no auth -> {r.status_code}")
        return True
    record_fail("POST /api/auth/locale no auth", f"expected 401 got {r.status_code}")
    return False


def test_locale_persistence_in_mongo():
    # Set to es, then check via /auth/me whether locale field is present
    r = requests.post(f"{API}/auth/locale", headers=auth_headers(TOKEN), json={"locale": "es"}, timeout=15)
    if r.status_code != 200:
        record_fail("locale persistence setup", r.text)
        return False
    me = requests.get(f"{API}/auth/me", headers=auth_headers(TOKEN), timeout=15)
    if me.status_code != 200:
        record_fail("locale persistence /auth/me", me.text)
        return False
    me_data = me.json()
    if me_data.get("locale") != "es":
        record_fail("locale persistence", f"/auth/me locale={me_data.get('locale')}")
        return False
    record_pass("locale persisted in user document (verified via /auth/me)")
    return True


# =========================================================================
# 2. AI plan localization
# =========================================================================
def looks_spanish(text: str) -> (bool, str):
    if not text:
        return False, "empty summary"
    t = text.lower()
    spanish_markers = ["á", "é", "í", "ó", "ú", "ñ", "¡", "¿"]
    spanish_words = [" tu ", " para ", " semana", " plan", " que ", " con ", " los ", " las ", " es ", " una ", " del ", " por ", "objetivo", "meta", "guitarra", "aprender", "tocar"]
    if any(m in t for m in spanish_markers):
        hits = [m for m in spanish_markers if m in t]
        return True, f"accents: {hits}"
    if sum(1 for w in spanish_words if w in t) >= 2:
        hits = [w.strip() for w in spanish_words if w in t]
        return True, f"keywords: {hits}"
    # English-only markers
    english_markers = [" the ", " your ", " you ", " for ", " week", " goal", " practice", " learn"]
    eh = [w.strip() for w in english_markers if w in t]
    return False, f"no spanish markers; english-like markers: {eh}"


def test_ai_plan_localized_spanish():
    # Ensure locale is es
    requests.post(f"{API}/auth/locale", headers=auth_headers(TOKEN), json={"locale": "es"}, timeout=15)

    # Free plan only allows 1 active goal — clean up any existing active goals first
    list_r = requests.get(f"{API}/goals", headers=auth_headers(TOKEN), timeout=15)
    if list_r.status_code == 200:
        for g in list_r.json():
            if g.get("status") == "active":
                requests.delete(f"{API}/goals/{g['id']}", headers=auth_headers(TOKEN), timeout=15)

    payload = {
        "title": "Aprender a tocar guitarra",
        "deadline": "2026-09-30",
        "motivation": "Quiero impresionar a mis amigos en una fiesta.",
        "current_level": "beginner",
        "hours_per_week": 5,
    }
    r = requests.post(f"{API}/goals", headers=auth_headers(TOKEN), json=payload, timeout=120)
    if r.status_code != 200:
        record_fail("AI plan localization /goals POST", f"status={r.status_code} body={r.text[:300]}")
        return False
    goal = r.json()
    plan = goal.get("plan") or {}
    summary = plan.get("summary", "")
    print(f"AI plan summary (es): {summary!r}")
    is_es, reason = looks_spanish(summary)
    if is_es:
        record_pass("AI plan summary in Spanish", reason)
        return True
    # Tolerate AI flakiness only if summary has any non-ASCII or some Spanish word
    record_fail("AI plan summary not in Spanish", f"summary={summary!r} | reason={reason}")
    return False


# =========================================================================
# 3. POST /api/webhook/stripe
# =========================================================================
def test_webhook_bad_signature():
    r = requests.post(
        f"{API}/webhook/stripe",
        data=b"{}",
        headers={"Stripe-Signature": "bad", "Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code != 400:
        record_fail("webhook bad signature", f"expected 400 got {r.status_code} body={r.text}")
        return False
    if "Invalid webhook" not in r.text:
        record_warn("webhook 400 detail mismatch", r.text)
    record_pass("POST /api/webhook/stripe bad signature -> 400")
    return True


def test_webhook_idempotency_marker():
    """We can't fully simulate paid because StripeCheckout signature validation will fail without secret bypass.
    Just verify 400 is consistent and existing user plan unchanged after multiple invalid calls.
    Also insert a paid txn doc in DB and verify webhook still 400s and user plan untouched.
    """
    # Capture current plan
    me0 = requests.get(f"{API}/auth/me", headers=auth_headers(TOKEN), timeout=15).json()
    plan_before = me0.get("plan")

    # Insert a payment_transactions doc directly via mongo
    try:
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "goalpilot_db")

        async def insert_paid_doc():
            cli = AsyncIOMotorClient(mongo_url)
            db = cli[db_name]
            sid = f"cs_test_{uuid.uuid4().hex[:16]}"
            await db.payment_transactions.insert_one({
                "id": str(uuid.uuid4()),
                "session_id": sid,
                "user_id": USER_ID,
                "user_email": EMAIL,
                "package_id": "pro_monthly",
                "plan": "pro",
                "billing": "monthly",
                "amount": 12.00,
                "currency": "usd",
                "payment_status": "paid",
                "status": "complete",
                "metadata": {},
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            })
            cli.close()
            return sid

        sid = asyncio.get_event_loop().run_until_complete(insert_paid_doc()) if False else asyncio.run(insert_paid_doc())
        print(f"Inserted paid txn session_id={sid}")
    except Exception as e:
        record_warn("could not insert mongo doc directly", str(e))

    # Multiple bad-signature posts
    for _ in range(3):
        r = requests.post(
            f"{API}/webhook/stripe",
            data=b"{}",
            headers={"Stripe-Signature": "bad", "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code != 400:
            record_fail("webhook idempotency consistency", f"got {r.status_code}")
            return False

    me1 = requests.get(f"{API}/auth/me", headers=auth_headers(TOKEN), timeout=15).json()
    plan_after = me1.get("plan")
    if plan_before != plan_after:
        record_fail("webhook should not have changed user plan", f"{plan_before} -> {plan_after}")
        return False
    record_pass("webhook 400 consistent + user plan unchanged after invalid posts")
    return True


# =========================================================================
# 4. Regression on existing endpoints
# =========================================================================
def test_login():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    if r.status_code != 200 or "token" not in r.json():
        record_fail("/api/auth/login", f"{r.status_code} {r.text}")
        return False
    record_pass("/api/auth/login")
    return True


def test_me():
    r = requests.get(f"{API}/auth/me", headers=auth_headers(TOKEN), timeout=15)
    if r.status_code != 200 or r.json().get("id") != USER_ID:
        record_fail("/api/auth/me", f"{r.status_code} {r.text}")
        return False
    record_pass("/api/auth/me")
    return True


def test_goals_get():
    r = requests.get(f"{API}/goals", headers=auth_headers(TOKEN), timeout=15)
    if r.status_code != 200 or not isinstance(r.json(), list):
        record_fail("/api/goals GET", f"{r.status_code} {r.text}")
        return False
    record_pass(f"/api/goals GET ({len(r.json())} goals)")
    return True


def test_dashboard_stats():
    r = requests.get(f"{API}/dashboard/stats", headers=auth_headers(TOKEN), timeout=15)
    if r.status_code != 200:
        record_fail("/api/dashboard/stats", f"{r.status_code} {r.text}")
        return False
    body = r.json()
    expected = {"today_total", "today_done", "today_pct", "active_goals", "total_completed", "missed", "streak"}
    if not expected.issubset(body.keys()):
        record_fail("/api/dashboard/stats keys", f"missing: {expected - set(body.keys())}")
        return False
    record_pass(f"/api/dashboard/stats {body}")
    return True


def test_nudge():
    r = requests.get(f"{API}/nudge", headers=auth_headers(TOKEN), timeout=15)
    if r.status_code != 200:
        record_fail("/api/nudge", f"{r.status_code} {r.text}")
        return False
    body = r.json()
    if "show" not in body:
        record_fail("/api/nudge body", f"missing 'show': {body}")
        return False
    record_pass(f"/api/nudge show={body.get('show')}")
    return True


def test_review_weekly():
    r = requests.get(f"{API}/review/weekly", headers=auth_headers(TOKEN), timeout=120)
    if r.status_code != 200:
        record_fail("/api/review/weekly", f"{r.status_code} {r.text}")
        return False
    body = r.json()
    expected = {"completed", "missed", "total_due", "completion_rate", "summary", "suggestion"}
    if not expected.issubset(body.keys()):
        record_fail("/api/review/weekly keys", f"missing: {expected - set(body.keys())}")
        return False
    record_pass(f"/api/review/weekly summary_len={len(body.get('summary',''))}")
    return True


# Run all
print("\n========== Running tests ==========\n")
test_locale_happy_paths()
test_locale_unsupported()
test_locale_no_auth()
test_locale_persistence_in_mongo()

test_ai_plan_localized_spanish()

test_webhook_bad_signature()
test_webhook_idempotency_marker()

test_login()
test_me()
test_goals_get()
test_dashboard_stats()
test_nudge()
test_review_weekly()

print("\n========== Summary ==========")
print(f"Passed: {len(results['passed'])}")
print(f"Failed: {len(results['failed'])}")
print(f"Warnings: {len(results['warnings'])}")
for n, info in results["failed"]:
    print(f"  FAIL: {n} -- {info}")
for n, info in results["warnings"]:
    print(f"  WARN: {n} -- {info}")
sys.exit(0 if not results["failed"] else 1)
