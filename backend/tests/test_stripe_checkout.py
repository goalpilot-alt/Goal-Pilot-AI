"""GoalPilot AI - Tests for Stripe Checkout integration via emergentintegrations.

Covers:
- POST /api/checkout/session valid packages (pro_monthly, pro_annual, coach_monthly, coach_annual)
- POST /api/checkout/session invalid package -> 400
- POST /api/checkout/session no auth -> 401
- payment_transactions Mongo record created with status=open, payment_status=initiated, amount from server
- Server-side amount enforcement: amounts cannot be overridden by request body
- GET /api/checkout/status/{invalid_session_id} -> 404
- GET /api/checkout/status no auth -> 401
- Regression: /api/auth/me, /api/goals, /api/tasks/today, /api/nudge,
  /api/calendar/url, /api/calendar/export.ics, /api/review/weekly,
  /api/subscription/upgrade (legacy), /api/dashboard/stats
"""
import os
import uuid
import asyncio
import pytest
import requests

from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SEED_EMAIL = "tester@goalpilot.ai"
SEED_PASSWORD = "Test@1234"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "goalpilot_db")

PACKAGES_EXPECTED = {
    "pro_monthly":   {"plan": "pro",   "billing": "monthly", "amount": 12.00},
    "pro_annual":    {"plan": "pro",   "billing": "annual",  "amount": 108.00},
    "coach_monthly": {"plan": "coach", "billing": "monthly", "amount": 29.00},
    "coach_annual":  {"plan": "coach", "billing": "annual",  "amount": 252.00},
}

state = {}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- Auth seed ----------
def test_login_or_register_seed_user(s):
    r = s.post(f"{API}/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    if r.status_code != 200:
        email = f"stripetester_{uuid.uuid4().hex[:8]}@goalpilot.ai"
        rr = s.post(f"{API}/auth/register", json={"email": email, "password": SEED_PASSWORD, "name": "Stripe Tester"})
        assert rr.status_code == 200, rr.text
        data = rr.json()
        state["email"] = email
    else:
        data = r.json()
        state["email"] = SEED_EMAIL
    assert "token" in data
    state["token"] = data["token"]
    state["user_id"] = data["user"]["id"]
    state["headers"] = {"Authorization": f"Bearer {data['token']}"}


# ---------- Stripe Checkout Session (auth) ----------
def test_checkout_session_requires_auth(s):
    r = s.post(f"{API}/checkout/session", json={"package_id": "pro_monthly", "origin_url": BASE_URL})
    assert r.status_code in (401, 403), r.text


def test_checkout_session_invalid_package_400(s):
    r = s.post(
        f"{API}/checkout/session",
        json={"package_id": "totally_fake_pkg", "origin_url": BASE_URL},
        headers=state["headers"],
    )
    assert r.status_code == 400, r.text
    assert "package" in r.json().get("detail", "").lower()


@pytest.mark.parametrize("package_id", ["pro_monthly", "pro_annual", "coach_monthly", "coach_annual"])
def test_checkout_session_valid_package_creates_session(s, package_id):
    r = s.post(
        f"{API}/checkout/session",
        json={"package_id": package_id, "origin_url": BASE_URL},
        headers=state["headers"],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "url" in data and isinstance(data["url"], str)
    assert "session_id" in data and isinstance(data["session_id"], str)
    # Stripe Checkout URL
    assert data["url"].startswith("https://"), f"unexpected checkout url: {data['url']}"
    assert "stripe.com" in data["url"], f"checkout url is not on stripe.com: {data['url']}"
    state.setdefault("sessions", {})[package_id] = data["session_id"]


def test_payment_transactions_persisted_in_mongo():
    """Verify the Mongo record was written with server-side amount + status=open."""
    sessions = state.get("sessions", {})
    assert sessions, "no sessions captured from previous test"

    async def _check():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            db = client[DB_NAME]
            for pkg_id, sess_id in sessions.items():
                expected = PACKAGES_EXPECTED[pkg_id]
                tx = await db.payment_transactions.find_one({"session_id": sess_id}, {"_id": 0})
                assert tx is not None, f"no payment_transactions row for {pkg_id} / {sess_id}"
                # status fields
                assert tx.get("status") == "open", f"{pkg_id}: expected status=open got {tx.get('status')}"
                assert tx.get("payment_status") == "initiated", (
                    f"{pkg_id}: expected payment_status=initiated got {tx.get('payment_status')}"
                )
                # SERVER-SIDE AMOUNT ENFORCEMENT — amount must come from PACKAGES dict
                assert float(tx.get("amount")) == float(expected["amount"]), (
                    f"{pkg_id}: amount mismatch. tx={tx.get('amount')} expected={expected['amount']}"
                )
                assert tx.get("currency") == "usd"
                assert tx.get("plan") == expected["plan"]
                assert tx.get("billing") == expected["billing"]
                assert tx.get("user_id") == state["user_id"]
                assert tx.get("package_id") == pkg_id
        finally:
            client.close()

    asyncio.get_event_loop().run_until_complete(_check())


def test_checkout_session_ignores_client_amount_override(s):
    """Even if a client tries to send `amount` in the body, server uses PACKAGES dict.

    Pydantic model only declares package_id + origin_url, so extra fields are dropped,
    and the resulting tx amount must equal the server-side PACKAGES value.
    """
    r = s.post(
        f"{API}/checkout/session",
        json={"package_id": "pro_monthly", "origin_url": BASE_URL, "amount": 0.01, "currency": "eur"},
        headers=state["headers"],
    )
    assert r.status_code == 200, r.text
    sess_id = r.json()["session_id"]

    async def _check():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            tx = await client[DB_NAME].payment_transactions.find_one({"session_id": sess_id}, {"_id": 0})
            assert tx is not None
            assert float(tx["amount"]) == 12.00, f"amount override leaked: {tx['amount']}"
            assert tx["currency"] == "usd", f"currency override leaked: {tx['currency']}"
        finally:
            client.close()

    asyncio.get_event_loop().run_until_complete(_check())


# ---------- Checkout status ----------
def test_checkout_status_requires_auth(s):
    r = s.get(f"{API}/checkout/status/cs_test_invalid_xyz")
    assert r.status_code in (401, 403), r.text


def test_checkout_status_invalid_session_404(s):
    r = s.get(
        f"{API}/checkout/status/cs_does_not_exist_{uuid.uuid4().hex}",
        headers=state["headers"],
    )
    assert r.status_code == 404, r.text


def test_checkout_status_for_real_session_returns_pending_or_open(s):
    """After fix: even if upstream Stripe lookup fails (proxy-issued session),
    endpoint must 200 with local fallback (payment_status=initiated, status=open,
    amount_total=cents-from-package, currency, plan, billing)."""
    sessions = state.get("sessions", {})
    assert sessions, "needs at least one created session"
    # Use pro_monthly so we know the expected amount_total deterministically
    pkg_id = "pro_monthly"
    sess_id = sessions[pkg_id]
    r = s.get(f"{API}/checkout/status/{sess_id}", headers=state["headers"])
    assert r.status_code == 200, f"expected 200 (fallback), got {r.status_code}: {r.text}"
    data = r.json()
    # Required keys
    for k in ("payment_status", "status", "amount_total", "currency", "plan", "billing"):
        assert k in data, f"missing key {k} in response: {data}"
    # No card has been entered, so payment_status should not be 'paid'
    assert data["payment_status"] != "paid", f"unexpected paid status: {data}"
    # On Stripe-failure fallback we expect initiated/open from local row
    assert data["payment_status"] in ("initiated", "unpaid", "open"), data["payment_status"]
    assert data["status"] in ("open", "complete", "expired"), data["status"]
    # amount_total must be cents from PACKAGES (12.00 -> 1200)
    expected_cents = int(PACKAGES_EXPECTED[pkg_id]["amount"] * 100)
    assert data["amount_total"] == expected_cents, (
        f"amount_total mismatch: got {data['amount_total']} expected {expected_cents}"
    )
    assert data["currency"] == "usd"
    assert data["plan"] == PACKAGES_EXPECTED[pkg_id]["plan"]
    assert data["billing"] == PACKAGES_EXPECTED[pkg_id]["billing"]


def test_checkout_status_idempotent_when_already_paid(s):
    """If tx.payment_status is already 'paid' in mongo, endpoint must return paid
    WITHOUT calling Stripe. We force the row to paid then call the endpoint."""
    sessions = state.get("sessions", {})
    assert sessions, "needs at least one created session"
    pkg_id = "coach_monthly"
    sess_id = sessions[pkg_id]

    async def _flip_paid():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            res = await client[DB_NAME].payment_transactions.update_one(
                {"session_id": sess_id},
                {"$set": {"payment_status": "paid", "status": "complete"}},
            )
            assert res.matched_count == 1, f"no tx for {sess_id}"
        finally:
            client.close()

    asyncio.get_event_loop().run_until_complete(_flip_paid())

    r = s.get(f"{API}/checkout/status/{sess_id}", headers=state["headers"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["payment_status"] == "paid", data
    assert data["status"] == "complete", data
    expected_cents = int(PACKAGES_EXPECTED[pkg_id]["amount"] * 100)
    assert data["amount_total"] == expected_cents
    assert data["currency"] == "usd"
    assert data["plan"] == PACKAGES_EXPECTED[pkg_id]["plan"]
    assert data["billing"] == PACKAGES_EXPECTED[pkg_id]["billing"]

    # Reset row so cleanup test still works and we don't accidentally upgrade plan
    async def _reset():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            await client[DB_NAME].payment_transactions.update_one(
                {"session_id": sess_id},
                {"$set": {"payment_status": "initiated", "status": "open"}},
            )
        finally:
            client.close()

    asyncio.get_event_loop().run_until_complete(_reset())


# ---------- Regression: existing endpoints still healthy ----------
def test_regression_auth_me(s):
    r = s.get(f"{API}/auth/me", headers=state["headers"])
    assert r.status_code == 200
    assert r.json()["email"].lower() == state["email"].lower()


def test_regression_goals_list(s):
    r = s.get(f"{API}/goals", headers=state["headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_regression_tasks_today(s):
    r = s.get(f"{API}/tasks/today", headers=state["headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_regression_nudge(s):
    r = s.get(f"{API}/nudge", headers=state["headers"])
    assert r.status_code == 200
    assert "show" in r.json()


def test_regression_calendar_url(s):
    r = s.get(f"{API}/calendar/url", headers=state["headers"])
    assert r.status_code == 200
    tok = r.json().get("token")
    assert tok and len(tok) > 20
    state["ics_token"] = tok


def test_regression_calendar_ics(s):
    assert state.get("ics_token")
    r = s.get(f"{API}/calendar/export.ics", params={"token": state["ics_token"]})
    assert r.status_code == 200
    assert "text/calendar" in r.headers.get("content-type", "").lower()
    assert r.text.startswith("BEGIN:VCALENDAR")
    assert "END:VCALENDAR" in r.text


def test_regression_review_weekly(s):
    r = s.get(f"{API}/review/weekly", headers=state["headers"])
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("completed", "missed", "total_due", "completion_rate", "summary", "suggestion"):
        assert k in d


def test_regression_subscription_upgrade_legacy(s):
    # legacy mock — should still flip plan
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": "pro", "billing": "monthly"},
        headers=state["headers"],
    )
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"


def test_regression_dashboard_stats(s):
    r = s.get(f"{API}/dashboard/stats", headers=state["headers"])
    assert r.status_code == 200
    d = r.json()
    for k in ("today_total", "today_done", "today_pct", "active_goals", "streak", "missed"):
        assert k in d


# ---------- Cleanup ----------
def test_cleanup_reset_to_free(s):
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": "free", "billing": "monthly"},
        headers=state["headers"],
    )
    assert r.status_code == 200
