import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from core.auth import get_current_user, get_user_locale
from core.config import PLAN_GOAL_LIMITS
from core.db import db
from models.schemas import GoalCreateReq
from services.ai import generate_ai_plan

router = APIRouter()
logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL_HOURS = 24


@router.post('/goals')
async def create_goal(
    req: GoalCreateReq,
    user: dict = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(default=None, alias='X-Idempotency-Key'),
):
    # ---- Idempotency: replay cached response if same key seen recently ----
    if x_idempotency_key:
        cached = await db.idempotency_keys.find_one({
            'user_id': user['id'],
            'key': x_idempotency_key,
        }, {'_id': 0})
        if cached:
            ts = cached.get('created_at')
            try:
                created = datetime.fromisoformat(ts) if ts else None
            except Exception:
                created = None
            if created and (datetime.now(timezone.utc) - created) < timedelta(hours=IDEMPOTENCY_TTL_HOURS):
                logger.info(f"Idempotent goal replay for user={user['id']} key={x_idempotency_key}")
                if cached.get('status_code') == 402:
                    raise HTTPException(status_code=402, detail=cached.get('detail', 'Plan limit reached'))
                return cached.get('response') or {'ok': True}

    # ---- Plan-based active-goal cap ----
    plan = user.get('plan', 'free')
    limit = PLAN_GOAL_LIMITS.get(plan, 1)
    if limit is not None:
        count = await db.goals.count_documents({'user_id': user['id'], 'status': 'active'})
        if count >= limit:
            if plan == 'free':
                detail = 'Free plan allows 1 active goal. Upgrade to Pro for up to 5.'
            elif plan == 'pro':
                detail = 'Pro plan allows 5 active goals. Upgrade to Coach for unlimited.'
            else:
                detail = f'Plan limit reached ({limit} active goals).'
            # cache 402 too so client retries with same key get same answer
            if x_idempotency_key:
                await db.idempotency_keys.update_one(
                    {'user_id': user['id'], 'key': x_idempotency_key},
                    {'$set': {
                        'user_id': user['id'],
                        'key': x_idempotency_key,
                        'status_code': 402,
                        'detail': detail,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    }},
                    upsert=True,
                )
            raise HTTPException(status_code=402, detail=detail)

    # ---- Create goal ----
    goal_id = str(uuid.uuid4())
    goal_doc = {
        'id': goal_id,
        'user_id': user['id'],
        'title': req.title,
        'deadline': req.deadline,
        'motivation': req.motivation,
        'current_level': req.current_level,
        'hours_per_week': req.hours_per_week,
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'plan': None,
    }

    try:
        ai_plan = await generate_ai_plan(goal_doc, await get_user_locale(user))
        goal_doc['plan'] = ai_plan
    except Exception as e:
        logger.error(f'AI generation failed: {e}')
        # Do NOT create an empty goal — surface a clear error so user can retry
        raise HTTPException(
            status_code=503,
            detail="We couldn't generate your plan right now. Please try again in a moment.",
        )

    await db.goals.insert_one(goal_doc.copy())

    now = datetime.now(timezone.utc)
    task_docs = []
    for t in goal_doc['plan'].get('daily_tasks', []):
        day_offset = t.get('day_offset', 0)
        due = (now + timedelta(days=day_offset)).date().isoformat()
        task_docs.append({
            'id': str(uuid.uuid4()),
            'user_id': user['id'],
            'goal_id': goal_id,
            'title': t.get('title', 'Task'),
            'priority': t.get('priority', 'medium'),
            'est_minutes': t.get('est_minutes', 30),
            'due_date': due,
            'completed': False,
            'completed_at': None,
            'created_at': now.isoformat(),
        })
    if task_docs:
        await db.tasks.insert_many(task_docs)

    goal_doc.pop('_id', None)

    # cache success response for idempotency
    if x_idempotency_key:
        await db.idempotency_keys.update_one(
            {'user_id': user['id'], 'key': x_idempotency_key},
            {'$set': {
                'user_id': user['id'],
                'key': x_idempotency_key,
                'status_code': 200,
                'goal_id': goal_id,
                'response': goal_doc,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )

    return goal_doc


@router.get('/goals')
async def list_goals(user: dict = Depends(get_current_user)):
    cursor = db.goals.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1)
    return await cursor.to_list(100)


@router.get('/goals/{goal_id}')
async def get_goal(goal_id: str, user: dict = Depends(get_current_user)):
    goal = await db.goals.find_one({'id': goal_id, 'user_id': user['id']}, {'_id': 0})
    if not goal:
        raise HTTPException(status_code=404, detail='Goal not found')
    return goal


@router.delete('/goals/{goal_id}')
async def delete_goal(goal_id: str, user: dict = Depends(get_current_user)):
    res = await db.goals.delete_one({'id': goal_id, 'user_id': user['id']})
    await db.tasks.delete_many({'goal_id': goal_id, 'user_id': user['id']})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Goal not found')
    return {'ok': True}


class ReplanReq(BaseModel):
    deadline: str  # YYYY-MM-DD


@router.post('/goals/{goal_id}/replan')
async def replan_goal(goal_id: str, req: ReplanReq, user: dict = Depends(get_current_user)):
    """Re-run AI plan generation with a new deadline. Replaces all existing tasks for this goal."""
    goal = await db.goals.find_one({'id': goal_id, 'user_id': user['id']}, {'_id': 0})
    if not goal:
        raise HTTPException(status_code=404, detail='Goal not found')

    # Validate new deadline is in the future
    try:
        new_deadline = datetime.fromisoformat(req.deadline).date()
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid deadline format (YYYY-MM-DD)')
    today = datetime.now(timezone.utc).date()
    if new_deadline <= today:
        raise HTTPException(status_code=400, detail='Deadline must be in the future')

    goal['deadline'] = req.deadline
    try:
        ai_plan = await generate_ai_plan(goal, await get_user_locale(user))
    except Exception as e:
        logger.error(f'Replan AI generation failed: {e}')
        raise HTTPException(status_code=500, detail='AI plan generation failed')

    # Replace goal + tasks atomically (delete old tasks, then insert new ones)
    await db.goals.update_one(
        {'id': goal_id, 'user_id': user['id']},
        {'$set': {
            'deadline': req.deadline,
            'plan': ai_plan,
            'replanned_at': datetime.now(timezone.utc).isoformat(),
        }},
    )
    await db.tasks.delete_many({'goal_id': goal_id, 'user_id': user['id']})

    now = datetime.now(timezone.utc)
    for t in ai_plan.get('daily_tasks', []) or []:
        day_offset = int(t.get('day_offset', 0) or 0)
        due = (now + timedelta(days=day_offset)).date().isoformat()
        await db.tasks.insert_one({
            'id': str(uuid.uuid4()),
            'user_id': user['id'],
            'goal_id': goal_id,
            'title': t.get('title', 'Task'),
            'priority': t.get('priority', 'medium'),
            'est_minutes': t.get('est_minutes', 30),
            'due_date': due,
            'completed': False,
            'completed_at': None,
            'created_at': now.isoformat(),
        })

    updated = await db.goals.find_one({'id': goal_id, 'user_id': user['id']}, {'_id': 0})
    return updated
