"""GoalPilot AI - Tests for new features: nudge, calendar sync, annual billing.

Covers:
- GET /api/nudge (streak recovery nudge)
- GET /api/calendar/url (JWT token for subscription URL)
- GET /api/calendar/export.ics (ICS content with VEVENTs)
- POST /api/subscription/upgrade with billing=annual and invalid billing
- Regression: auth + existing user login
"""
import os
import re
import uuid
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

# Pre-existing tester account (see /app/memory/test_credentials.md). Fall back to register a fresh one if needed.
SEED_EMAIL = "tester@goalpilot.ai"
SEED_PASSWORD = "Test@1234"

state = {}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- Auth / setup ----------
def test_login_or_register_seed_user(s):
    r = s.post(f"{API}/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    if r.status_code != 200:
        # fallback: create a fresh unique user
        email = f"nudgetester_{uuid.uuid4().hex[:8]}@goalpilot.ai"
        rr = s.post(f"{API}/auth/register", json={"email": email, "password": SEED_PASSWORD, "name": "Nudge Tester"})
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


# ---------- Nudge ----------
def test_nudge_returns_valid_shape(s):
    r = s.get(f"{API}/nudge", headers=state["headers"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert "show" in data
    if data["show"]:
        # must have all expected fields
        for k in ("title", "message", "days_since", "suggested_task"):
            assert k in data, f"missing {k} in nudge response"
        assert isinstance(data["title"], str) and len(data["title"]) > 0
        assert isinstance(data["message"], str) and len(data["message"]) > 0
        # days_since is int or None
        assert data["days_since"] is None or isinstance(data["days_since"], int)


def test_nudge_requires_auth(s):
    r = s.get(f"{API}/nudge")
    assert r.status_code == 401


# ---------- Calendar URL ----------
def test_calendar_url_returns_token(s):
    r = s.get(f"{API}/calendar/url", headers=state["headers"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data
    assert isinstance(data["token"], str) and len(data["token"]) > 20
    state["ics_token"] = data["token"]


def test_calendar_url_requires_auth(s):
    r = s.get(f"{API}/calendar/url")
    assert r.status_code == 401


# ---------- Calendar ICS export ----------
def test_calendar_ics_invalid_token_401(s):
    r = s.get(f"{API}/calendar/export.ics", params={"token": "not-a-jwt"})
    assert r.status_code == 401


def test_calendar_ics_valid_token_returns_vcalendar(s):
    assert state.get("ics_token"), "requires test_calendar_url_returns_token first"
    r = s.get(f"{API}/calendar/export.ics", params={"token": state["ics_token"]})
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "text/calendar" in ct.lower(), f"unexpected content-type {ct}"
    body = r.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert "END:VCALENDAR" in body
    assert "PRODID:-//GoalPilot AI//EN" in body
    assert "VERSION:2.0" in body
    # VEVENT blocks appear when user has tasks or goals (seed user has a goal from prior test run)
    # We don't strictly require any VEVENT, but if present they must be well-formed.
    if "BEGIN:VEVENT" in body:
        assert body.count("BEGIN:VEVENT") == body.count("END:VEVENT")
        # DTSTAMP must be present per VEVENT
        vevents = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", body, re.DOTALL)
        for ev in vevents:
            assert "UID:" in ev
            assert "DTSTAMP:" in ev
            assert "DTSTART" in ev
            assert "SUMMARY:" in ev


# ---------- Subscription w/ annual billing ----------
def test_upgrade_pro_annual(s):
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": "pro", "billing": "annual"},
        headers=state["headers"],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "pro"
    assert data["billing"] == "annual"
    # verify persisted
    me = s.get(f"{API}/auth/me", headers=state["headers"]).json()
    assert me["plan"] == "pro"
    assert me.get("billing") == "annual"


def test_upgrade_coach_monthly(s):
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": "coach", "billing": "monthly"},
        headers=state["headers"],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "coach"
    assert data["billing"] == "monthly"


def test_upgrade_invalid_billing_400(s):
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": "pro", "billing": "lifetime"},
        headers=state["headers"],
    )
    assert r.status_code == 400, r.text


def test_upgrade_invalid_plan_400(s):
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": "ultra", "billing": "monthly"},
        headers=state["headers"],
    )
    assert r.status_code == 400


# ---------- Regression: basic flows still work ----------
def test_me_endpoint(s):
    r = s.get(f"{API}/auth/me", headers=state["headers"])
    assert r.status_code == 200
    assert r.json()["email"].lower() == state["email"].lower()


def test_dashboard_stats(s):
    r = s.get(f"{API}/dashboard/stats", headers=state["headers"])
    assert r.status_code == 200
    d = r.json()
    for k in ("today_total", "today_done", "today_pct", "active_goals", "streak", "missed"):
        assert k in d


def test_tasks_today(s):
    r = s.get(f"{API}/tasks/today", headers=state["headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# Reset to free plan monthly so subsequent test iterations start clean
def test_reset_to_free(s):
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": "free", "billing": "monthly"},
        headers=state["headers"],
    )
    assert r.status_code == 200
