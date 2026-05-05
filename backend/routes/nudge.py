from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from core.auth import get_current_user
from core.db import db

router = APIRouter()


@router.get('/nudge')
async def get_nudge(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()

    last = await db.tasks.find_one(
        {'user_id': user['id'], 'completed': True},
        sort=[('completed_at', -1)],
        projection={'_id': 0, 'completed_at': 1, 'title': 1},
    )
    days_since = None
    if last and last.get('completed_at'):
        last_date = datetime.fromisoformat(last['completed_at']).date()
        days_since = (today - last_date).days

    easy_task = await db.tasks.find_one(
        {'user_id': user['id'], 'completed': False, 'priority': {'$in': ['low', 'medium']}},
        sort=[('est_minutes', 1)],
        projection={'_id': 0},
    )

    show_nudge = days_since is None or days_since >= 1
    if not show_nudge:
        return {'show': False}

    if days_since is None:
        title = "Let's start your streak"
        message = 'Complete one small task today to kick off your momentum.'
    elif days_since == 1:
        title = "Don't break the chain"
        message = "It's been a day. One quick win keeps your streak alive."
    elif days_since <= 3:
        title = f'{days_since} days off-plan'
        message = 'Comebacks beat perfection. Pick the easiest task and win it now.'
    else:
        title = 'Restart, fresh'
        message = f"It's been {days_since} days. We've adapted your plan \u2014 start with one tiny task."

    return {
        'show': True,
        'title': title,
        'message': message,
        'days_since': days_since,
        'suggested_task': easy_task,
    }
