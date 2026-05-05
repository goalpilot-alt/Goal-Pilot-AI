"""GoalPilot AI - Tests for plan-based active-goal caps and push notification tokens.

Covers:
- Free plan: 1 active goal cap → 402 with 'Free plan allows 1 active goal'
- Pro plan: 5 active goals cap → 402 with 'Pro plan allows 5 active goals'
- Coach plan: unlimited active goals (creates 6 successfully)
- POST /api/notifications/token (auth, empty token, upsert behaviour)
- DELETE /api/notifications/token
- Regression: stripe checkout/session, status fallback, /api/auth/me, /api/goals,
  /api/tasks/today, /api/nudge, /api/calendar/url, /api/calendar/export.ics,
  /api/review/weekly, /api/dashboard/stats, /api/subscription/upgrade
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SEED_EMAIL = "tester@goalpilot.ai"
SEED_PASSWORD = "Test@1234"

state = {}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _auth_headers():
    return {"Authorization": f"Bearer {state['token']}"}


def _set_plan(s, plan: str, billing: str = "monthly"):
    r = s.post(
        f"{API}/subscription/upgrade",
        params={"plan": plan, "billing": billing},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, f"failed to set plan={plan}: {r.text}"


def _delete_all_goals(s):
    """Clear all goals for the test user before plan-cap tests."""
    r = s.get(f"{API}/goals", headers=_auth_headers())
    assert r.status_code == 200
    for g in r.json():
        s.delete(f"{API}/goals/{g['id']}", headers=_auth_headers())


def _make_goal_payload(title: str = "TEST_Goal"):
    return {
        "title": f"TEST_{title}_{uuid.uuid4().hex[:6]}",
        "deadline": "2026-12-31",
        "motivation": "test motivation",
        "current_level": "beginner",
        "hours_per_week": 5,
    }


# ---------- Setup: login or register seed user ----------
def test_login_or_register_seed_user(s):
    r = s.post(f"{API}/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    if r.status_code != 200:
        rr = s.post(f"{API}/auth/register", json={"email": SEED_EMAIL, "password": SEED_PASSWORD, "name": "Tester"})
        assert rr.status_code == 200, rr.text
        data = rr.json()
    else:
        data = r.json()
    assert "token" in data
    state["token"] = data["token"]
    state["user_id"] = data["user"]["id"]
    state["email"] = data["user"]["email"]


def test_cleanup_initial_state(s):
    """Reset to free plan and clear all goals before plan-cap testing."""
    _set_plan(s, "free", "monthly")
    _delete_all_goals(s)
    # verify
    r = s.get(f"{API}/goals", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() == []


# ---------- Plan-based active-goal caps ----------
class TestFreePlanCap:
    def test_free_first_goal_succeeds(self, s):
        _set_plan(s, "free")
        r = s.post(f"{API}/goals", json=_make_goal_payload("free1"), headers=_auth_headers())
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "active"
        state["free_goal_id"] = body["id"]

    def test_free_second_goal_returns_402(self, s):
        r = s.post(f"{API}/goals", json=_make_goal_payload("free2"), headers=_auth_headers())
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        assert "Free plan allows 1 active goal" in detail, f"unexpected detail: {detail}"

    def test_free_cleanup(self, s):
        _delete_all_goals(s)


class TestProPlanCap:
    def test_pro_creates_5_goals(self, s):
        _set_plan(s, "pro")
        for i in range(5):
            r = s.post(f"{API}/goals", json=_make_goal_payload(f"pro{i}"), headers=_auth_headers())
            assert r.status_code == 200, f"pro goal #{i+1} failed: {r.text}"

    def test_pro_sixth_goal_returns_402(self, s):
        r = s.post(f"{API}/goals", json=_make_goal_payload("pro6"), headers=_auth_headers())
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        assert "Pro plan allows 5 active goals" in detail, f"unexpected detail: {detail}"

    def test_pro_cleanup(self, s):
        _delete_all_goals(s)


class TestCoachPlanUnlimited:
    def test_coach_creates_more_than_5_goals(self, s):
        _set_plan(s, "coach")
        for i in range(6):
            r = s.post(f"{API}/goals", json=_make_goal_payload(f"coach{i}"), headers=_auth_headers())
            assert r.status_code == 200, f"coach goal #{i+1} failed: {r.text}"
        # Verify we have at least 6 active goals (no cap)
        r = s.get(f"{API}/goals", headers=_auth_headers())
        assert r.status_code == 200
        active = [g for g in r.json() if g.get("status") == "active"]
        assert len(active) >= 6, f"expected >=6 active goals, got {len(active)}"

    def test_coach_cleanup(self, s):
        _delete_all_goals(s)
        # reset to free for downstream regression tests
        _set_plan(s, "free")


# ---------- Push notification tokens ----------
class TestPushTokens:
    def test_post_token_no_auth_returns_401(self, s):
        r = requests.post(f"{API}/notifications/token", json={"token": "ExpoPushToken[abc]", "platform": "ios"})
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}: {r.text}"

    def test_post_token_empty_returns_400(self, s):
        r = s.post(
            f"{API}/notifications/token",
            json={"token": "", "platform": "ios"},
            headers=_auth_headers(),
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        assert "token" in r.json().get("detail", "").lower()

    def test_post_token_persists_and_upserts(self, s):
        token_a = f"ExpoPushToken[TEST_{uuid.uuid4().hex[:8]}]"
        # First insert
        r1 = s.post(
            f"{API}/notifications/token",
            json={"token": token_a, "platform": "ios"},
            headers=_auth_headers(),
        )
        assert r1.status_code == 200, r1.text
        assert r1.json().get("ok") is True

        # Re-post same token+user → upsert (no duplicate row, no error)
        r2 = s.post(
            f"{API}/notifications/token",
            json={"token": token_a, "platform": "android"},
            headers=_auth_headers(),
        )
        assert r2.status_code == 200, r2.text
        state["push_token_a"] = token_a

    def test_post_token_default_platform(self, s):
        token_b = f"ExpoPushToken[TEST_{uuid.uuid4().hex[:8]}]"
        r = s.post(
            f"{API}/notifications/token",
            json={"token": token_b},  # no platform
            headers=_auth_headers(),
        )
        assert r.status_code == 200, r.text
        state["push_token_b"] = token_b

    def test_delete_token_removes_row(self, s):
        token = state.get("push_token_a")
        assert token, "requires test_post_token_persists_and_upserts first"
        r = s.delete(
            f"{API}/notifications/token",
            params={"token": token},
            headers=_auth_headers(),
        )
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_delete_token_no_auth_returns_401(self, s):
        r = requests.delete(f"{API}/notifications/token", params={"token": "anything"})
        assert r.status_code in (401, 403)

    def test_cleanup_push_token_b(self, s):
        token = state.get("push_token_b")
        if token:
            s.delete(
                f"{API}/notifications/token",
                params={"token": token},
                headers=_auth_headers(),
            )


# ---------- Regression ----------
class TestRegression:
    def test_auth_me(self, s):
        r = s.get(f"{API}/auth/me", headers=_auth_headers())
        assert r.status_code == 200
        assert r.json()["email"].lower() == SEED_EMAIL.lower()

    def test_goals_listing(self, s):
        r = s.get(f"{API}/goals", headers=_auth_headers())
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_tasks_today(self, s):
        r = s.get(f"{API}/tasks/today", headers=_auth_headers())
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_nudge(self, s):
        r = s.get(f"{API}/nudge", headers=_auth_headers())
        assert r.status_code == 200
        assert "show" in r.json()

    def test_calendar_url(self, s):
        r = s.get(f"{API}/calendar/url", headers=_auth_headers())
        assert r.status_code == 200
        token = r.json().get("token")
        assert token and len(token) > 20
        state["ics_token"] = token

    def test_calendar_ics_export(self, s):
        token = state.get("ics_token")
        assert token
        r = s.get(f"{API}/calendar/export.ics", params={"token": token})
        assert r.status_code == 200
        assert "text/calendar" in r.headers.get("content-type", "").lower()
        assert r.text.startswith("BEGIN:VCALENDAR")
        assert "END:VCALENDAR" in r.text

    def test_review_weekly(self, s):
        r = s.get(f"{API}/review/weekly", headers=_auth_headers())
        assert r.status_code == 200
        d = r.json()
        for k in ("completed", "missed", "total_due", "completion_rate", "summary", "suggestion"):
            assert k in d

    def test_dashboard_stats(self, s):
        r = s.get(f"{API}/dashboard/stats", headers=_auth_headers())
        assert r.status_code == 200
        d = r.json()
        for k in ("today_total", "today_done", "today_pct", "active_goals", "streak", "missed"):
            assert k in d

    def test_subscription_upgrade_legacy(self, s):
        r = s.post(
            f"{API}/subscription/upgrade",
            params={"plan": "pro", "billing": "monthly"},
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["plan"] == "pro"
        # reset to free
        _set_plan(s, "free")

    def test_stripe_checkout_session_creation(self, s):
        r = s.post(
            f"{API}/checkout/session",
            json={"package_id": "pro_monthly", "origin_url": "https://example.com"},
            headers=_auth_headers(),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "url" in body and "session_id" in body
        assert body["url"].startswith("https://")
        state["checkout_session_id"] = body["session_id"]

    def test_stripe_checkout_status_fallback_200(self, s):
        sid = state.get("checkout_session_id")
        assert sid
        r = s.get(f"{API}/checkout/status/{sid}", headers=_auth_headers())
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("payment_status", "status", "amount_total", "currency", "plan", "billing"):
            assert k in body
        assert body["plan"] == "pro"
        assert body["billing"] == "monthly"
        assert body["currency"] == "usd"
        assert body["amount_total"] == 1200  # $12.00

    def test_stripe_webhook_endpoint_exists(self, s):
        # without a valid signature, expect 400 (handled by handle_webhook)
        r = requests.post(f"{API}/webhook/stripe", data=b"{}", headers={"Stripe-Signature": "invalid"})
        assert r.status_code in (400, 422), f"expected 400/422, got {r.status_code}: {r.text}"


# ---------- Final cleanup ----------
def test_final_reset_to_free(s):
    _set_plan(s, "free", "monthly")
    _delete_all_goals(s)
