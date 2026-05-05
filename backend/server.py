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
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
)

# ---------- Setup ----------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGO = "HS256"
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
STRIPE_API_KEY = os.environ['STRIPE_API_KEY']
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Server-side plan catalog — NEVER trust amounts from client
PACKAGES = {
    "pro_monthly":    {"plan": "pro",   "billing": "monthly", "amount": 12.00, "currency": "usd"},
    "pro_annual":     {"plan": "pro",   "billing": "annual",  "amount": 108.00, "currency": "usd"},
    "coach_monthly":  {"plan": "coach", "billing": "monthly", "amount": 29.00, "currency": "usd"},
    "coach_annual":   {"plan": "coach", "billing": "annual",  "amount": 252.00, "currency": "usd"},
}

# Active-goals cap by plan (None = unlimited)
PLAN_GOAL_LIMITS = {"free": 1, "pro": 5, "coach": None}

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


class CheckoutSessionReq(BaseModel):
    package_id: str
    origin_url: str  # from window.location.origin / app deep-link origin


class PushTokenReq(BaseModel):
    token: str
    platform: Optional[str] = None  # 'ios' | 'android' | 'web'


class LocaleReq(BaseModel):
    locale: str


SUPPORTED_LOCALES = {"en-US", "en-GB", "es", "fr", "cs", "sk", "ru", "zh-CN"}

# Friendly names for the AI prompts so it knows what language to respond in
LOCALE_LANGUAGE_NAMES = {
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "es":    "Spanish (Español)",
    "fr":    "French (Français)",
    "cs":    "Czech (Čeština)",
    "sk":    "Slovak (Slovenčina)",
    "ru":    "Russian (Русский)",
    "zh-CN": "Simplified Chinese (中文 简体)",
}


async def get_user_locale(user: dict) -> str:
    loc = user.get("locale") or "en-US"
    return loc if loc in SUPPORTED_LOCALES else "en-US"


def lang_instruction(locale: str) -> str:
    name = LOCALE_LANGUAGE_NAMES.get(locale, "English (US)")
    return f"Respond entirely in {name}. All field values in the JSON must be written in {name}."


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


@api.post("/auth/locale")
async def set_locale(req: LocaleReq, user: dict = Depends(get_current_user)):
    if req.locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail="Unsupported locale")
    await db.users.update_one({"id": user["id"]}, {"$set": {"locale": req.locale}})
    return {"ok": True, "locale": req.locale}


# ---------- AI Plan Generation ----------
async def generate_ai_plan(goal: dict, locale: str = "en-US") -> dict:
    session_id = f"goal-{goal['id']}"
    system_msg = (
        "You are GoalPilot AI, an expert coach and planner. "
        "You receive a user goal and produce a structured JSON plan. "
        "Be specific, motivating and realistic. Return ONLY valid JSON, no markdown. "
        + lang_instruction(locale)
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
    # Plan-based active-goal cap
    plan = user.get("plan", "free")
    limit = PLAN_GOAL_LIMITS.get(plan, 1)
    if limit is not None:
        count = await db.goals.count_documents({"user_id": user["id"], "status": "active"})
        if count >= limit:
            if plan == "free":
                detail = "Free plan allows 1 active goal. Upgrade to Pro for up to 5."
            elif plan == "pro":
                detail = "Pro plan allows 5 active goals. Upgrade to Coach for unlimited."
            else:
                detail = f"Plan limit reached ({limit} active goals)."
            raise HTTPException(status_code=402, detail=detail)

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
        ai_plan = await generate_ai_plan(goal_doc, await get_user_locale(user))
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
            system_message="You are an AI accountability coach. Be warm, specific, motivating. Return ONLY JSON. " + lang_instruction(await get_user_locale(user)),
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


# ---------- Stripe Checkout ----------
@api.post("/checkout/session")
async def create_checkout_session(req: CheckoutSessionReq, http_request: Request, user: dict = Depends(get_current_user)):
    if req.package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    pkg = PACKAGES[req.package_id]

    origin = req.origin_url.rstrip("/")
    success_url = f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing"

    host_url = str(http_request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    metadata = {
        "user_id": user["id"],
        "user_email": user["email"],
        "package_id": req.package_id,
        "plan": pkg["plan"],
        "billing": pkg["billing"],
    }

    checkout_req = CheckoutSessionRequest(
        amount=pkg["amount"],
        currency=pkg["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    session: CheckoutSessionResponse = await checkout.create_checkout_session(checkout_req)

    # Record transaction as initiated BEFORE returning
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "package_id": req.package_id,
        "plan": pkg["plan"],
        "billing": pkg["billing"],
        "amount": pkg["amount"],
        "currency": pkg["currency"],
        "payment_status": "initiated",
        "status": "open",
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"url": session.url, "session_id": session.session_id}


@api.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If already finalized, return stored state (idempotent)
    if tx.get("payment_status") == "paid":
        return {
            "payment_status": "paid",
            "status": tx.get("status", "complete"),
            "amount_total": int(tx["amount"] * 100),
            "currency": tx["currency"],
            "plan": tx["plan"],
            "billing": tx["billing"],
        }

    # Try to refresh from Stripe; on failure, fall back to local state so polling never 500s.
    try:
        checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        status: CheckoutStatusResponse = await checkout.get_checkout_status(session_id)
        update = {
            "payment_status": status.payment_status,
            "status": status.status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

        # Only grant plan once per session
        if status.payment_status == "paid" and tx.get("payment_status") != "paid":
            await db.users.update_one(
                {"id": user["id"]},
                {"$set": {"plan": tx["plan"], "billing": tx["billing"], "upgraded_at": datetime.now(timezone.utc).isoformat()}},
            )

        return {
            "payment_status": status.payment_status,
            "status": status.status,
            "amount_total": status.amount_total,
            "currency": status.currency,
            "plan": tx["plan"],
            "billing": tx["billing"],
        }
    except Exception as e:
        logger.warning(f"Stripe status lookup failed for {session_id}: {e}. Falling back to local state.")
        return {
            "payment_status": tx.get("payment_status", "unpaid"),
            "status": tx.get("status", "open"),
            "amount_total": int(tx["amount"] * 100),
            "currency": tx["currency"],
            "plan": tx["plan"],
            "billing": tx["billing"],
        }


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint to confirm payment & upgrade plan asynchronously.

    Validated using STRIPE_WEBHOOK_SECRET when present. Idempotent — safe to retry.
    """
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_secret=STRIPE_WEBHOOK_SECRET or None)
    try:
        event = await checkout.handle_webhook(body, signature)
    except Exception as e:
        logger.error(f"Stripe webhook validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")

    event_type = getattr(event, "event_type", None) or getattr(event, "type", None)
    logger.info(f"Stripe webhook received: type={event_type} session={event.session_id} status={event.payment_status}")

    if event.payment_status == "paid" and event.session_id:
        tx = await db.payment_transactions.find_one({"session_id": event.session_id})
        if not tx:
            logger.warning(f"Webhook paid for unknown session_id={event.session_id}")
            return {"ok": True, "ignored": True}
        if tx.get("payment_status") == "paid":
            # Already processed — idempotent no-op
            return {"ok": True, "already_processed": True}

        await db.payment_transactions.update_one(
            {"session_id": event.session_id},
            {"$set": {
                "payment_status": "paid",
                "status": "complete",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "webhook_event_type": event_type,
            }},
        )
        await db.users.update_one(
            {"id": tx["user_id"]},
            {"$set": {
                "plan": tx["plan"],
                "billing": tx["billing"],
                "upgraded_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"User {tx['user_id']} upgraded via webhook to {tx['plan']}/{tx['billing']}")

    return {"ok": True}


# ---------- Legacy Mock (kept for backward compat; do not use for real upgrades) ----------
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


# ---------- Push Notification Tokens ----------
@api.post("/notifications/token")
async def save_push_token(req: PushTokenReq, user: dict = Depends(get_current_user)):
    if not req.token:
        raise HTTPException(status_code=400, detail="Missing token")
    await db.push_tokens.update_one(
        {"user_id": user["id"], "token": req.token},
        {"$set": {
            "user_id": user["id"],
            "token": req.token,
            "platform": req.platform or "unknown",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {"ok": True}


@api.delete("/notifications/token")
async def remove_push_token(token: str, user: dict = Depends(get_current_user)):
    await db.push_tokens.delete_one({"user_id": user["id"], "token": token})
    return {"ok": True}


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
