"""GoalPilot AI - Backend integration tests."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://6f33189a-fd72-4bf9-a9e7-1965bdac1597.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

UNIQUE = uuid.uuid4().hex[:8]
EMAIL = f"tester_{UNIQUE}@goalpilot.ai"
PASSWORD = "Test@1234"
NAME = "Tester"

state = {}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---- Auth ----
def test_root(s):
    r = s.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_register(s):
    r = s.post(f"{API}/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": NAME})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == EMAIL
    assert data["user"]["plan"] == "free"
    state["token"] = data["token"]
    state["user_id"] = data["user"]["id"]


def test_register_duplicate(s):
    r = s.post(f"{API}/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": NAME})
    assert r.status_code == 400


def test_login(s):
    r = s.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    assert "token" in r.json()


def test_login_wrong_pw(s):
    r = s.post(f"{API}/auth/login", json={"email": EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_me(s):
    r = s.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL


def test_me_no_auth(s):
    r = s.get(f"{API}/auth/me")
    assert r.status_code == 401


# ---- Goals + AI ----
def test_create_goal(s):
    headers = {"Authorization": f"Bearer {state['token']}"}
    payload = {
        "title": "Learn Spanish basics",
        "deadline": "2026-06-01",
        "motivation": "Travel to Spain confidently",
        "current_level": "beginner",
        "hours_per_week": 5,
    }
    r = s.post(f"{API}/goals", json=payload, headers=headers, timeout=90)
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["title"] == payload["title"]
    assert "plan" in g and g["plan"] is not None
    plan = g["plan"]
    assert "summary" in plan
    assert isinstance(plan.get("milestones"), list)
    assert isinstance(plan.get("weekly_plan"), list)
    assert isinstance(plan.get("daily_tasks"), list)
    state["goal_id"] = g["id"]


def test_list_goals(s):
    r = s.get(f"{API}/goals", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    goals = r.json()
    assert any(g["id"] == state["goal_id"] for g in goals)


def test_get_goal(s):
    r = s.get(f"{API}/goals/{state['goal_id']}", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    assert r.json()["id"] == state["goal_id"]


def test_free_plan_second_goal_blocked(s):
    headers = {"Authorization": f"Bearer {state['token']}"}
    payload = {
        "title": "Second goal",
        "deadline": "2026-06-01",
        "motivation": "x",
        "current_level": "beginner",
        "hours_per_week": 3,
    }
    r = s.post(f"{API}/goals", json=payload, headers=headers, timeout=90)
    assert r.status_code == 402, r.text


# ---- Tasks ----
def test_tasks_today(s):
    r = s.get(f"{API}/tasks/today", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    tasks = r.json()
    assert isinstance(tasks, list)
    # day_offset 0 tasks should be present
    state["task_id"] = tasks[0]["id"] if tasks else None


def test_tasks_missed(s):
    r = s.get(f"{API}/tasks/missed", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_toggle_task(s):
    if not state.get("task_id"):
        pytest.skip("No today task to toggle")
    tid = state["task_id"]
    headers = {"Authorization": f"Bearer {state['token']}"}
    r = s.patch(f"{API}/tasks/{tid}", json={"completed": True}, headers=headers)
    assert r.status_code == 200
    assert r.json()["completed"] is True
    # toggle back
    r2 = s.patch(f"{API}/tasks/{tid}", json={"completed": False}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["completed"] is False


# ---- Dashboard / Review ----
def test_dashboard_stats(s):
    r = s.get(f"{API}/dashboard/stats", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    d = r.json()
    for k in ("today_total", "today_done", "today_pct", "active_goals", "streak", "missed"):
        assert k in d


def test_weekly_review(s):
    r = s.get(f"{API}/review/weekly", headers={"Authorization": f"Bearer {state['token']}"}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "summary" in d and "suggestion" in d
    assert isinstance(d.get("completion_rate"), int)


# ---- Subscription (mocked) ----
def test_upgrade_pro(s):
    r = s.post(f"{API}/subscription/upgrade?plan=pro", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"
    me = s.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {state['token']}"}).json()
    assert me["plan"] == "pro"


def test_upgrade_invalid_plan(s):
    r = s.post(f"{API}/subscription/upgrade?plan=ultra", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 400


# ---- Cleanup ----
def test_delete_goal(s):
    r = s.delete(f"{API}/goals/{state['goal_id']}", headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    r2 = s.get(f"{API}/goals/{state['goal_id']}", headers={"Authorization": f"Bearer {state['token']}"})
    assert r2.status_code == 404
