from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends

from core.auth import get_current_user, get_user_locale
from core.db import db
from services.ai import generate_weekly_review

router = APIRouter()


@router.get('/dashboard/stats')
async def dashboard_stats(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date().isoformat()
    total_today = await db.tasks.count_documents({'user_id': user['id'], 'due_date': today})
    done_today = await db.tasks.count_documents({'user_id': user['id'], 'due_date': today, 'completed': True})
    active_goals = await db.goals.count_documents({'user_id': user['id'], 'status': 'active'})
    total_completed = await db.tasks.count_documents({'user_id': user['id'], 'completed': True})
    missed = await db.tasks.count_documents({
        'user_id': user['id'],
        'due_date': {'$lt': today},
        'completed': False,
    })

    # Calculate streak: fetch distinct completion dates in last 60 days with a single query
    since_date = (datetime.now(timezone.utc).date() - timedelta(days=60)).isoformat()
    completed_docs = await db.tasks.find(
        {'user_id': user['id'], 'completed': True, 'due_date': {'$gte': since_date}},
        {'_id': 0, 'due_date': 1},
    ).to_list(500)
    completed_dates = {t['due_date'] for t in completed_docs if t.get('due_date')}
    streak = 0
    today_date = datetime.now(timezone.utc).date()
    for i in range(0, 60):
        d = (today_date - timedelta(days=i)).isoformat()
        if d in completed_dates:
            streak += 1
        else:
            if i == 0:
                # Skip today if empty (streak from yesterday still counts)
                continue
            break

    pct = int((done_today / total_today) * 100) if total_today > 0 else 0
    return {
        'today_total': total_today,
        'today_done': done_today,
        'today_pct': pct,
        'active_goals': active_goals,
        'total_completed': total_completed,
        'missed': missed,
        'streak': streak,
    }


@router.get('/review/weekly')
async def weekly_review(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    week_ago = (today - timedelta(days=7)).isoformat()
    today_s = today.isoformat()

    completed = await db.tasks.count_documents({
        'user_id': user['id'],
        'completed': True,
        'completed_at': {'$gte': week_ago},
    })
    missed = await db.tasks.count_documents({
        'user_id': user['id'],
        'due_date': {'$gte': week_ago, '$lt': today_s},
        'completed': False,
    })
    total_due = await db.tasks.count_documents({
        'user_id': user['id'],
        'due_date': {'$gte': week_ago, '$lt': today_s},
    })

    goals = await db.goals.find({'user_id': user['id'], 'status': 'active'}, {'_id': 0}).to_list(5)
    goal_titles = ', '.join([g['title'] for g in goals]) or 'no active goals'

    locale = await get_user_locale(user)
    summary_text, suggestion = await generate_weekly_review(
        user['id'], locale, completed, missed, total_due, goal_titles, today_s
    )

    return {
        'completed': completed,
        'missed': missed,
        'total_due': total_due,
        'completion_rate': int((completed / total_due) * 100) if total_due > 0 else 0,
        'summary': summary_text,
        'suggestion': suggestion,
    }
