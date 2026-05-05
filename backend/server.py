from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import json
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from emergentintegrations.llm.chat import LlmChat, UserMessage

# ---------- Setup ----------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGO = "HS256"
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

app = FastAPI()
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- Helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------- Models ----------
class RegisterReq(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class AuthResp(BaseModel):
    token: str
    user: dict


class GoalCreateReq(BaseModel):
    title: str
    deadline: str  # ISO date
    motivation: str
    current_level: str  # beginner/intermediate/advanced
    hours_per_week: int


class TaskToggleReq(BaseModel):
    completed: bool


# ---------- Auth Endpoints ----------
@api.post("/auth/register", response_model=AuthResp)
async def register(req: RegisterReq):
    email = req.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": email,
        "name": req.name,
        "password_hash": hash_password(req.password),
        "plan": "free",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(user_id, email)
    user_out = {k: v for k, v in user_doc.items() if k not in ("_id", "password_hash")}
    return {"token": token, "user": user_out}


@api.post("/auth/login", response_model=AuthResp)
async def login(req: LoginReq):
    email = req.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user["id"], email)
    user_out = {k: v for k, v in user.items() if k not in ("_id", "password_hash")}
    return {"token": token, "user": user_out}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ---------- AI Plan Generation ----------
async def generate_ai_plan(goal: dict) -> dict:
    session_id = f"goal-{goal['id']}"
    system_msg = (
        "You are GoalPilot AI, an expert coach and planner. "
        "You receive a user goal and produce a structured JSON plan. "
        "Be specific, motivating and realistic. Return ONLY valid JSON, no markdown."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_msg,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    deadline = goal["deadline"]
    prompt = f"""Create a practical plan for this goal.

Goal: {goal['title']}
Deadline: {deadline}
Motivation: {goal['motivation']}
Current level: {goal['current_level']}
Time per week: {goal['hours_per_week']} hours

Return JSON with this EXACT shape:
{{
  "summary": "2-3 sentence inspiring summary of the plan",
  "why_it_works": "Short paragraph on why this plan leads to success",
  "milestones": [
    {{"title": "Milestone name", "target_date": "YYYY-MM-DD", "description": "what they will achieve"}}
  ],
  "weekly_plan": [
    {{"week": 1, "focus": "theme", "goals": ["...", "..."]}}
  ],
  "daily_tasks": [
    {{"title": "Task name", "priority": "high|medium|low", "est_minutes": 30, "day_offset": 0}}
  ]
}}

Create 3-5 milestones, 4 weeks of weekly_plan, and 5-7 daily_tasks starting day_offset 0 (today).
"""
    response = await chat.send_message(UserMessage(text=prompt))
    # Strip markdown fencing if present
    text = response.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except Exception as e:
        logger.error(f"AI parse error: {e}\nRaw: {text[:500]}")
        # Fallback structure
        return {
            "summary": "Your AI plan is being prepared. Keep going!",
            "why_it_works": "Consistent small actions compound into results.",
            "milestones": [],
            "weekly_plan": [],
            "daily_tasks": [],
        }


# ---------- Goals Endpoints ----------
@api.post("/goals")
async def create_goal(req: GoalCreateReq, user: dict = Depends(get_current_user)):
    # Free plan: 1 active goal
    if user.get("plan", "free") == "free":
        count = await db.goals.count_documents({"user_id": user["id"], "status": "active"})
        if count >= 1:
            raise HTTPException(status_code=402, detail="Free plan allows 1 active goal. Upgrade to Pro.")

    goal_id = str(uuid.uuid4())
    goal_doc = {
        "id": goal_id,
        "user_id": user["id"],
        "title": req.title,
        "deadline": req.deadline,
        "motivation": req.motivation,
        "current_level": req.current_level,
        "hours_per_week": req.hours_per_week,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan": None,
    }

    # Generate AI plan
    try:
        ai_plan = await generate_ai_plan(goal_doc)
        goal_doc["plan"] = ai_plan
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        goal_doc["plan"] = {"summary": "AI plan generation failed", "milestones": [], "weekly_plan": [], "daily_tasks": []}

    await db.goals.insert_one(goal_doc.copy())

    # Create task docs from daily_tasks
    now = datetime.now(timezone.utc)
    for t in goal_doc["plan"].get("daily_tasks", []):
        day_offset = t.get("day_offset", 0)
        due = (now + timedelta(days=day_offset)).date().isoformat()
        await db.tasks.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "goal_id": goal_id,
            "title": t.get("title", "Task"),
            "priority": t.get("priority", "medium"),
            "est_minutes": t.get("est_minutes", 30),
            "due_date": due,
            "completed": False,
            "completed_at": None,
            "created_at": now.isoformat(),
        })

    goal_doc.pop("_id", None)
    return goal_doc


@api.get("/goals")
async def list_goals(user: dict = Depends(get_current_user)):
    cursor = db.goals.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(100)


@api.get("/goals/{goal_id}")
async def get_goal(goal_id: str, user: dict = Depends(get_current_user)):
    goal = await db.goals.find_one({"id": goal_id, "user_id": user["id"]}, {"_id": 0})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@api.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user: dict = Depends(get_current_user)):
    res = await db.goals.delete_one({"id": goal_id, "user_id": user["id"]})
    await db.tasks.delete_many({"goal_id": goal_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"ok": True}


# ---------- Tasks Endpoints ----------
@api.get("/tasks/today")
async def tasks_today(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date().isoformat()
    cursor = db.tasks.find({"user_id": user["id"], "due_date": today}, {"_id": 0}).sort("priority", 1)
    return await cursor.to_list(200)


@api.get("/tasks/missed")
async def tasks_missed(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date().isoformat()
    cursor = db.tasks.find({
        "user_id": user["id"],
        "due_date": {"$lt": today},
        "completed": False,
    }, {"_id": 0}).sort("due_date", -1).limit(20)
    return await cursor.to_list(20)


@api.get("/tasks")
async def list_tasks(goal_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"user_id": user["id"]}
    if goal_id:
        q["goal_id"] = goal_id
    cursor = db.tasks.find(q, {"_id": 0}).sort("due_date", 1)
    return await cursor.to_list(500)


@api.patch("/tasks/{task_id}")
async def toggle_task(task_id: str, req: TaskToggleReq, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat() if req.completed else None
    res = await db.tasks.update_one(
        {"id": task_id, "user_id": user["id"]},
        {"$set": {"completed": req.completed, "completed_at": now}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return task


# ---------- Dashboard Stats ----------
@api.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date().isoformat()
    total_today = await db.tasks.count_documents({"user_id": user["id"], "due_date": today})
    done_today = await db.tasks.count_documents({"user_id": user["id"], "due_date": today, "completed": True})
    active_goals = await db.goals.count_documents({"user_id": user["id"], "status": "active"})
    total_completed = await db.tasks.count_documents({"user_id": user["id"], "completed": True})
    missed = await db.tasks.count_documents({
        "user_id": user["id"],
        "due_date": {"$lt": today},
        "completed": False,
    })

    # Streak (consecutive days with >=1 completed task)
    streak = 0
    for i in range(0, 60):
        d = (datetime.now(timezone.utc).date() - timedelta(days=i)).isoformat()
        c = await db.tasks.count_documents({"user_id": user["id"], "due_date": d, "completed": True})
        if c > 0:
            streak += 1
        else:
            if i == 0:
                continue  # today zero still, don't break immediately
            break

    pct = int((done_today / total_today) * 100) if total_today > 0 else 0
    return {
        "today_total": total_today,
        "today_done": done_today,
        "today_pct": pct,
        "active_goals": active_goals,
        "total_completed": total_completed,
        "missed": missed,
        "streak": streak,
    }


# ---------- Weekly Review ----------
@api.get("/review/weekly")
async def weekly_review(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    week_ago = (today - timedelta(days=7)).isoformat()
    today_s = today.isoformat()

    completed = await db.tasks.count_documents({
        "user_id": user["id"],
        "completed": True,
        "completed_at": {"$gte": week_ago},
    })
    missed = await db.tasks.count_documents({
        "user_id": user["id"],
        "due_date": {"$gte": week_ago, "$lt": today_s},
        "completed": False,
    })
    total_due = await db.tasks.count_documents({
        "user_id": user["id"],
        "due_date": {"$gte": week_ago, "$lt": today_s},
    })

    # AI summary
    goals = await db.goals.find({"user_id": user["id"], "status": "active"}, {"_id": 0}).to_list(5)
    goal_titles = ", ".join([g["title"] for g in goals]) or "no active goals"

    summary_text = ""
    suggestion = ""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"review-{user['id']}-{today_s}",
            system_message="You are an AI accountability coach. Be warm, specific, motivating. Return ONLY JSON.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        prompt = f"""User progress last 7 days:
- Tasks completed: {completed}
- Tasks missed: {missed}
- Total tasks due: {total_due}
- Active goals: {goal_titles}

Return JSON:
{{"summary": "2-3 sentences celebrating wins & acknowledging misses", "suggestion": "1 specific actionable focus for next week"}}"""
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        parsed = json.loads(text)
        summary_text = parsed.get("summary", "")
        suggestion = parsed.get("suggestion", "")
    except Exception as e:
        logger.error(f"Review AI failed: {e}")
        summary_text = f"This week you completed {completed} tasks. Keep building momentum!"
        suggestion = "Focus on finishing your top priority task each morning."

    return {
        "completed": completed,
        "missed": missed,
        "total_due": total_due,
        "completion_rate": int((completed / total_due) * 100) if total_due > 0 else 0,
        "summary": summary_text,
        "suggestion": suggestion,
    }


# ---------- Mock Subscription ----------
@api.post("/subscription/upgrade")
async def upgrade(plan: str, billing: str = "monthly", user: dict = Depends(get_current_user)):
    if plan not in ("free", "pro", "coach"):
        raise HTTPException(status_code=400, detail="Invalid plan")
    if billing not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="Invalid billing cycle")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"plan": plan, "billing": billing, "upgraded_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "plan": plan, "billing": billing}


# ---------- Streak Recovery Nudge ----------
@api.get("/nudge")
async def get_nudge(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    today_s = today.isoformat()

    # Days since last completed task
    last = await db.tasks.find_one(
        {"user_id": user["id"], "completed": True},
        sort=[("completed_at", -1)],
        projection={"_id": 0, "completed_at": 1, "title": 1},
    )
    days_since = None
    if last and last.get("completed_at"):
        last_date = datetime.fromisoformat(last["completed_at"]).date()
        days_since = (today - last_date).days

    # Find an easy missed/today task to recommend
    easy_task = await db.tasks.find_one(
        {"user_id": user["id"], "completed": False, "priority": {"$in": ["low", "medium"]}},
        sort=[("est_minutes", 1)],
        projection={"_id": 0},
    )

    show_nudge = days_since is None or days_since >= 1
    if not show_nudge:
        return {"show": False}

    if days_since is None:
        title = "Let's start your streak"
        message = "Complete one small task today to kick off your momentum."
    elif days_since == 1:
        title = "Don't break the chain"
        message = "It's been a day. One quick win keeps your streak alive."
    elif days_since <= 3:
        title = f"{days_since} days off-plan"
        message = "Comebacks beat perfection. Pick the easiest task and win it now."
    else:
        title = "Restart, fresh"
        message = f"It's been {days_since} days. We've adapted your plan — start with one tiny task."

    return {
        "show": True,
        "title": title,
        "message": message,
        "days_since": days_since,
        "suggested_task": easy_task,
    }


# ---------- Calendar Sync (ICS export) ----------
@api.get("/calendar/export.ics")
async def calendar_ics(token: str):
    """Return .ics file. Auth via query token because calendar apps can't send headers."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    tasks = await db.tasks.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(50)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GoalPilot AI//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:GoalPilot AI",
    ]
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for t in tasks:
        due = t.get("due_date", "")
        if not due:
            continue
        dt = due.replace("-", "")
        uid = f"task-{t['id']}@goalpilot.ai"
        summary = (t.get("title") or "Task").replace("\n", " ")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{dt}",
            f"DTEND;VALUE=DATE:{dt}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:Priority: {t.get('priority','')} | {t.get('est_minutes',0)} min",
            "END:VEVENT",
        ]

    for g in goals:
        deadline = g.get("deadline", "")
        if not deadline:
            continue
        dt = deadline.replace("-", "")
        uid = f"goal-{g['id']}@goalpilot.ai"
        summary = f"GOAL DEADLINE: {g.get('title','')}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{dt}",
            f"DTEND;VALUE=DATE:{dt}",
            f"SUMMARY:{summary}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines)
    from fastapi.responses import Response
    return Response(content=body, media_type="text/calendar; charset=utf-8")


@api.get("/calendar/url")
async def calendar_url(user: dict = Depends(get_current_user)):
    """Return a webcal/https URL the user can subscribe to from their device calendar."""
    token = create_access_token(user["id"], user["email"])
    return {"token": token}


# ---------- Startup ----------
@app.on_event("startup")
async def on_start():
    await db.users.create_index("email", unique=True)
    await db.goals.create_index("user_id")
    await db.tasks.create_index([("user_id", 1), ("due_date", 1)])


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


@api.get("/")
async def root():
    return {"app": "GoalPilot AI", "status": "ok"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
