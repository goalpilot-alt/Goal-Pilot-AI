"""Tests for goal idempotency-key + scheduler push job."""
import os
import time
import uuid
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _mk_user():
    email = f"idem_{uuid.uuid4().hex[:8]}@goalpilot.ai"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Pass@1234", "name": "Idem Tester"
    }, timeout=10)
    r.raise_for_status()
    return r.json()["token"], email


def test_goal_idempotency_returns_same_goal_on_replay():
    token, _ = _mk_user()
    h = {"Authorization": f"Bearer {token}", "X-Idempotency-Key": str(uuid.uuid4())}
    body = {
        "title": "Run a 5K", "deadline": "2026-12-31",
        "motivation": "Get fit and feel strong.",
        "current_level": "beginner", "hours_per_week": 5,
    }
    r1 = requests.post(f"{API}/goals", json=body, headers=h, timeout=120)
    assert r1.status_code == 200, r1.text
    g1 = r1.json()
    r2 = requests.post(f"{API}/goals", json=body, headers=h, timeout=10)
    assert r2.status_code == 200, r2.text
    g2 = r2.json()
    assert g1["id"] == g2["id"], "Same idempotency key must return same goal id"

    # Different idempotency key (and only 1 active goal allowed for free) -> 402
    h2 = {**h, "X-Idempotency-Key": str(uuid.uuid4())}
    r3 = requests.post(f"{API}/goals", json=body, headers=h2, timeout=10)
    assert r3.status_code == 402


def test_goal_idempotency_replays_402_too():
    token, _ = _mk_user()
    h = {"Authorization": f"Bearer {token}"}
    body = {
        "title": "Goal A", "deadline": "2026-12-31", "motivation": "Just because.",
        "current_level": "beginner", "hours_per_week": 5,
    }
    r1 = requests.post(f"{API}/goals", json=body, headers=h, timeout=120)
    assert r1.status_code == 200
    # Now hit limit with an idempotency key
    key = str(uuid.uuid4())
    h2 = {**h, "X-Idempotency-Key": key}
    body2 = {**body, "title": "Goal B"}
    r2 = requests.post(f"{API}/goals", json=body2, headers=h2, timeout=10)
    assert r2.status_code == 402
    # Replay should also be 402 (cached)
    r3 = requests.post(f"{API}/goals", json=body2, headers=h2, timeout=10)
    assert r3.status_code == 402


def test_scheduler_endpoint_unchanged_health():
    r = requests.get(f"{API}/", timeout=5)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
