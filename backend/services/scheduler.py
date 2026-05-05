"""Daily push scheduler. Runs once a day (UTC) and sends one push per user.

Picks the most relevant message:
  - Streak nudge if user is at risk (no completion >= 1 day OR never completed any task)
  - Else: Morning summary if there are tasks due today
  - Else: skip
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.db import db
from core.config import PUSH_DAILY_HOUR_UTC, PUSH_DAILY_MINUTE_UTC
from services.push import send_expo_push

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None

# Localized templates. Falls back to en-US for any locale we don't translate here.
TEMPLATES = {
    'en-US': {
        'streak_start_title': "Let's start your streak",
        'streak_start_body':  'Complete one small task today to kick off your momentum.',
        'streak_day_title':   "Don't break the chain",
        'streak_day_body':    'A quick win keeps your streak alive.',
        'streak_back_title':  'Welcome back',
        'streak_back_body':   "It's been {n} days. We've adapted your plan \u2014 start with one tiny task.",
        'morning_title':      "Today's plan is ready",
        'morning_body_one':   '1 task today. Top priority: {top}',
        'morning_body_many':  '{n} tasks today. Top priority: {top}',
    },
    'es': {
        'streak_start_title': 'Empecemos tu racha',
        'streak_start_body':  'Completa una peque\u00f1a tarea hoy para iniciar tu impulso.',
        'streak_day_title':   'No rompas la cadena',
        'streak_day_body':    'Una peque\u00f1a victoria mantiene tu racha viva.',
        'streak_back_title':  'Bienvenido de nuevo',
        'streak_back_body':   'Han pasado {n} d\u00edas. Adaptamos tu plan \u2014 comienza con una tarea peque\u00f1a.',
        'morning_title':      'Tu plan de hoy est\u00e1 listo',
        'morning_body_one':   '1 tarea hoy. Prioridad: {top}',
        'morning_body_many':  '{n} tareas hoy. Prioridad: {top}',
    },
    'fr': {
        'streak_start_title': 'D\u00e9marrons votre s\u00e9rie',
        'streak_start_body':  'Compl\u00e9tez une petite t\u00e2che aujourd\u2019hui.',
        'streak_day_title':   'Ne brisez pas la cha\u00eene',
        'streak_day_body':    'Une petite victoire maintient votre s\u00e9rie.',
        'streak_back_title':  'Bon retour',
        'streak_back_body':   '{n} jours. Nous avons adapt\u00e9 votre plan \u2014 commencez petit.',
        'morning_title':      'Votre plan du jour est pr\u00eat',
        'morning_body_one':   '1 t\u00e2che aujourd\u2019hui. Priorit\u00e9 : {top}',
        'morning_body_many':  '{n} t\u00e2ches aujourd\u2019hui. Priorit\u00e9 : {top}',
    },
    'zh-CN': {
        'streak_start_title': '\u5f00\u542f\u4f60\u7684\u8fde\u80dc',
        'streak_start_body':  '\u4eca\u5929\u5b8c\u6210\u4e00\u9879\u5c0f\u4efb\u52a1\u5373\u53ef\u542f\u52a8\u80fd\u91cf\u3002',
        'streak_day_title':   '\u522b\u4e2d\u65ad\u8fde\u80dc',
        'streak_day_body':    '\u4e00\u4e2a\u5feb\u901f\u80dc\u5229\u5c31\u80fd\u4fdd\u6301\u8fde\u80dc\u3002',
        'streak_back_title':  '\u6b22\u8fce\u56de\u6765',
        'streak_back_body':   '\u5df2\u8fc7 {n} \u5929\u3002\u6211\u4eec\u4e3a\u4f60\u8c03\u6574\u4e86\u8ba1\u5212 \u2014 \u4ece\u4e00\u9879\u5c0f\u4efb\u52a1\u5f00\u59cb\u3002',
        'morning_title':      '\u4eca\u5929\u7684\u8ba1\u5212\u5df2\u51c6\u5907',
        'morning_body_one':   '\u4eca\u5929 1 \u9879\u4efb\u52a1\u3002\u9996\u8981\uff1a{top}',
        'morning_body_many':  '\u4eca\u5929 {n} \u9879\u4efb\u52a1\u3002\u9996\u8981\uff1a{top}',
    },
}


def _t(locale: str, key: str, **fmt) -> str:
    bag = TEMPLATES.get(locale) or TEMPLATES['en-US']
    val = bag.get(key) or TEMPLATES['en-US'].get(key, '')
    try:
        return val.format(**fmt) if fmt else val
    except Exception:
        return val


async def _build_user_message(user: dict) -> dict | None:
    """Pick the best push for one user. Returns None if no push should be sent."""
    locale = user.get('locale') or 'en-US'
    prefs = user.get('notification_prefs') or {}
    morning_on = prefs.get('morning', True)
    streak_on = prefs.get('streak', True)
    if not morning_on and not streak_on:
        return None

    today = datetime.now(timezone.utc).date()

    # Determine streak risk: when was the last completed task?
    last = await db.tasks.find_one(
        {'user_id': user['id'], 'completed': True},
        sort=[('completed_at', -1)],
        projection={'_id': 0, 'completed_at': 1},
    )
    days_since = None
    if last and last.get('completed_at'):
        try:
            last_date = datetime.fromisoformat(last['completed_at']).date()
            days_since = (today - last_date).days
        except Exception:
            days_since = None

    title: str | None = None
    body: str | None = None
    notif_type = 'morning'

    if days_since is None:
        if not streak_on:
            return None
        # never completed anything — streak start nudge
        title = _t(locale, 'streak_start_title')
        body = _t(locale, 'streak_start_body')
        notif_type = 'streak_start'
    elif days_since >= 4:
        if not streak_on:
            return None
        title = _t(locale, 'streak_back_title')
        body = _t(locale, 'streak_back_body', n=days_since)
        notif_type = 'streak_back'
    elif days_since >= 1:
        if not streak_on:
            return None
        title = _t(locale, 'streak_day_title')
        body = _t(locale, 'streak_day_body')
        notif_type = 'streak_day'
    else:
        if not morning_on:
            return None
        # On streak — morning summary if tasks today
        today_s = today.isoformat()
        cursor = db.tasks.find(
            {'user_id': user['id'], 'due_date': today_s, 'completed': False},
            {'_id': 0, 'title': 1, 'priority': 1},
        )
        tasks = await cursor.to_list(50)
        if not tasks:
            return None  # nothing to push today — user is on track
        # Pick highest priority task as 'top'
        prio_rank = {'high': 0, 'medium': 1, 'low': 2}
        tasks.sort(key=lambda t: prio_rank.get(t.get('priority', 'medium'), 1))
        top = (tasks[0].get('title') or 'your top task')[:80]
        n = len(tasks)
        title = _t(locale, 'morning_title')
        body = _t(locale, 'morning_body_one' if n == 1 else 'morning_body_many', n=n, top=top)
        notif_type = 'morning'

    return {
        'user_id': user['id'],
        'title': title,
        'body': body,
        'data': {'type': notif_type, 'days_since': days_since},
    }


async def daily_push_job():
    """Run once daily — send personalised pushes to all users that have at least one push token."""
    logger.info('Daily push job: starting')
    sent = 0
    skipped = 0
    failed = 0

    # Iterate over distinct user_ids in push_tokens
    user_ids = await db.push_tokens.distinct('user_id')
    if not user_ids:
        logger.info('Daily push job: no registered tokens, skipping')
        return

    for uid in user_ids:
        try:
            user = await db.users.find_one({'id': uid}, {'_id': 0, 'password_hash': 0})
            if not user:
                continue
            msg = await _build_user_message(user)
            if not msg:
                skipped += 1
                continue
            tokens = await db.push_tokens.find({'user_id': uid}, {'_id': 0, 'token': 1}).to_list(20)
            expo_msgs = []
            for tk in tokens:
                t = tk.get('token')
                if not t or not t.startswith('ExponentPushToken'):
                    continue
                expo_msgs.append({
                    'to': t,
                    'title': msg['title'],
                    'body': msg['body'],
                    'sound': 'default',
                    'priority': 'high',
                    'data': msg['data'],
                })
            if not expo_msgs:
                skipped += 1
                continue
            await send_expo_push(expo_msgs)
            await db.push_log.insert_one({
                'user_id': uid,
                'type': msg['data'].get('type'),
                'sent_at': datetime.now(timezone.utc).isoformat(),
                'count': len(expo_msgs),
            })
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f'Daily push job: user {uid} failed: {e}')

    logger.info(f'Daily push job: done sent={sent} skipped={skipped} failed={failed}')


def start_scheduler():
    """Start the APScheduler with the daily job. Idempotent."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    sched = AsyncIOScheduler(timezone='UTC')
    sched.add_job(
        daily_push_job,
        CronTrigger(hour=PUSH_DAILY_HOUR_UTC, minute=PUSH_DAILY_MINUTE_UTC, timezone='UTC'),
        id='daily_push',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    _scheduler = sched
    logger.info(f'Scheduler started: daily push at {PUSH_DAILY_HOUR_UTC:02d}:{PUSH_DAILY_MINUTE_UTC:02d} UTC')
    return sched


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
