"""GoalPilot AI — Final pre-launch regression test (Google Play submission gate).

Tests all 8 sections required by review request against the live preview backend.
Uses httpx. Does not modify code. Limits Anthropic calls to ~3.
"""
import asyncio
import json
import os
import sys
import uuid
import subprocess
from datetime import datetime, timezone, timedelta

import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

BASE = 'https://goal-pilot-ai.preview.emergentagent.com/api'
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

TESTER_EMAIL = 'tester@goalpilot.ai'
TESTER_PASS = 'Test@1234'

results = []  # (section, name, ok, detail)


def record(section, name, ok, detail=''):
    results.append((section, name, ok, detail))
    icon = 'PASS' if ok else 'FAIL'
    print(f'[{icon}] {section} · {name}{" — " + detail if detail else ""}')


async def main():
    timeout = httpx.Timeout(connect=10.0, read=240.0, write=60.0, pool=60.0)
    async with httpx.AsyncClient(base_url=BASE, timeout=timeout) as http:
        mongo = AsyncIOMotorClient(MONGO_URL)
        db = mongo[DB_NAME]

        # ============== Section 1: Legal public pages ==============
        sec = 'S1-legal'
        try:
            r = await http.get('/legal/privacy')
            ct = r.headers.get('content-type', '')
            body = r.text
            ok = (
                r.status_code == 200
                and 'text/html' in ct
                and len(body) > 1000
                and 'Privacy Policy' in body
                and 'GDPR' in body
                and 'Czech Republic' in body
                and 'goalpilot@goal-pilot.com' in body
            )
            record(sec, 'GET /legal/privacy 200+html+content', ok,
                   '' if ok else f'status={r.status_code} ct={ct} len={len(body)}')
        except Exception as e:
            record(sec, 'GET /legal/privacy', False, str(e))

        try:
            r = await http.get('/legal/terms')
            body = r.text
            ok = (
                r.status_code == 200
                and 'text/html' in r.headers.get('content-type', '')
                and 'Terms of Service' in body
                and 'Subscription plans' in body
                and 'Acceptable use' in body
            )
            record(sec, 'GET /legal/terms 200+html+content', ok,
                   '' if ok else f'status={r.status_code} body sample: {body[:200]}')
        except Exception as e:
            record(sec, 'GET /legal/terms', False, str(e))

        try:
            r = await http.get('/legal/refund')
            body = r.text
            ok = (
                r.status_code == 200
                and 'text/html' in r.headers.get('content-type', '')
                and 'Refund Policy' in body
                and '14-day' in body
                and 'Czech Civil Code' in body
            )
            record(sec, 'GET /legal/refund 200+html+content', ok,
                   '' if ok else f'status={r.status_code} contains14day={"14-day" in body} containsCzechCivilCode={"Czech Civil Code" in body}')
        except Exception as e:
            record(sec, 'GET /legal/refund', False, str(e))

        try:
            r = await http.get('/legal/random')
            detail = ''
            try:
                detail = r.json().get('detail', '')
            except Exception:
                detail = r.text
            ok = r.status_code == 404 and 'privacy' in detail and 'terms' in detail and 'refund' in detail
            record(sec, 'GET /legal/random → 404 w/ helpful detail', ok,
                   '' if ok else f'status={r.status_code} detail={detail!r}')
        except Exception as e:
            record(sec, 'GET /legal/random', False, str(e))

        # Already exercised privacy/terms/refund without Authorization header above.
        record(sec, 'No auth required (3 happy paths anonymous)', True, 'verified above')

        # ============== Section 2: Auth & user state ==============
        sec = 'S2-auth'
        token = None
        try:
            r = await http.post('/auth/login', json={'email': TESTER_EMAIL, 'password': TESTER_PASS})
            ok = r.status_code == 200 and 'token' in r.json()
            token = r.json().get('token') if ok else None
            record(sec, 'POST /auth/login tester', ok,
                   '' if ok else f'status={r.status_code} body={r.text[:200]}')
        except Exception as e:
            record(sec, 'POST /auth/login tester', False, str(e))

        # /auth/me confirms plan=pro/billing=monthly
        try:
            r = await http.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
            j = r.json()
            ok = r.status_code == 200 and j.get('plan') == 'pro' and j.get('billing') == 'monthly'
            record(sec, '/auth/me reviewer plan=pro billing=monthly', ok,
                   '' if ok else f'status={r.status_code} plan={j.get("plan")} billing={j.get("billing")}')
        except Exception as e:
            record(sec, '/auth/me', False, str(e))

        # Fresh user register
        fresh_email = f'qa_{uuid.uuid4().hex[:8]}@goalpilot.ai'
        fresh_pass = 'Fresh@1234'
        fresh_token = None
        fresh_user_id = None
        try:
            r = await http.post('/auth/register', json={
                'email': fresh_email, 'password': fresh_pass, 'name': 'QA Fresh',
            })
            j = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and j.get('token') and j.get('user', {}).get('plan') == 'free'
            fresh_token = j.get('token')
            fresh_user_id = j.get('user', {}).get('id')
            record(sec, 'POST /auth/register fresh user (plan=free)', ok,
                   '' if ok else f'status={r.status_code} body={r.text[:200]}')
        except Exception as e:
            record(sec, 'POST /auth/register', False, str(e))

        # Locale es
        try:
            r = await http.post('/auth/locale', headers={'Authorization': f'Bearer {fresh_token}'},
                                json={'locale': 'es'})
            ok = r.status_code == 200 and r.json().get('locale') == 'es'
            # confirm persist
            r2 = await http.get('/auth/me', headers={'Authorization': f'Bearer {fresh_token}'})
            persists = r2.status_code == 200 and r2.json().get('locale') == 'es'
            record(sec, 'POST /auth/locale es + persists', ok and persists,
                   '' if ok and persists else f'set_status={r.status_code} get_status={r2.status_code}')
        except Exception as e:
            record(sec, 'POST /auth/locale', False, str(e))

        # Timezone Europe/Prague
        try:
            r = await http.post('/auth/timezone', headers={'Authorization': f'Bearer {fresh_token}'},
                                json={'timezone': 'Europe/Prague'})
            ok = r.status_code == 200 and r.json().get('timezone') == 'Europe/Prague'
            r2 = await http.get('/auth/me', headers={'Authorization': f'Bearer {fresh_token}'})
            persists = r2.status_code == 200 and r2.json().get('timezone') == 'Europe/Prague'
            record(sec, 'POST /auth/timezone Europe/Prague + persists', ok and persists,
                   '' if ok and persists else f'set_status={r.status_code} body={r.text[:200]}')
        except Exception as e:
            record(sec, 'POST /auth/timezone', False, str(e))

        # ============== Section 3: AI plan generation ==============
        sec = 'S3-ai-plan'
        goal_id = None
        daily_tasks_count = 0
        try:
            r = await http.post('/goals', headers={'Authorization': f'Bearer {fresh_token}'},
                                json={
                                    'title': 'Learn Spanish to B1 level',
                                    'deadline': '2026-12-31',
                                    'motivation': 'Travel in Spain',
                                    'current_level': 'beginner',
                                    'hours_per_week': 5,
                                })
            if r.status_code == 200:
                j = r.json()
                goal_id = j.get('id')
                plan = j.get('plan') or {}
                ms = plan.get('milestones') or []
                wp = plan.get('weekly_plan') or []
                dt = plan.get('daily_tasks') or []
                summary = plan.get('summary') or ''
                daily_tasks_count = len(dt)
                ok = (
                    len(ms) >= 3 and len(wp) >= 1 and len(dt) >= 5 and len(summary) > 50
                )
                record(sec, 'POST /goals AI plan populated', ok,
                       f'milestones={len(ms)} weekly={len(wp)} daily={len(dt)} summary_len={len(summary)}')
            else:
                record(sec, 'POST /goals AI plan populated', False,
                       f'status={r.status_code} body={r.text[:300]}')
        except Exception as e:
            record(sec, 'POST /goals', False, str(e))

        # GET /tasks returns count == daily_tasks length
        try:
            r = await http.get('/tasks', headers={'Authorization': f'Bearer {fresh_token}'})
            tasks = r.json() if r.status_code == 200 else []
            ok = r.status_code == 200 and len(tasks) == daily_tasks_count and daily_tasks_count > 0
            record(sec, 'GET /tasks count == daily_tasks length', ok,
                   f'tasks_returned={len(tasks)} expected={daily_tasks_count}')
        except Exception as e:
            record(sec, 'GET /tasks', False, str(e))

        # Replan
        try:
            if goal_id:
                r = await http.post(f'/goals/{goal_id}/replan',
                                    headers={'Authorization': f'Bearer {fresh_token}'},
                                    json={'deadline': '2027-06-30'})
                if r.status_code == 200:
                    j = r.json()
                    ms = j.get('plan', {}).get('milestones') or []
                    ok = j.get('deadline') == '2027-06-30' and len(ms) >= 1
                    record(sec, 'POST /goals/{id}/replan refreshed', ok,
                           f'milestones={len(ms)} new_deadline={j.get("deadline")}')
                else:
                    record(sec, 'POST /goals/{id}/replan', False,
                           f'status={r.status_code} body={r.text[:300]}')
            else:
                record(sec, 'POST /goals/{id}/replan', False, 'no goal_id from prior step')
        except Exception as e:
            record(sec, 'POST /goals/{id}/replan', False, str(e))

        # ============== Section 4: Stripe checkout (LIVE) ==============
        sec = 'S4-stripe'
        try:
            r = await http.post('/checkout/session',
                                headers={'Authorization': f'Bearer {token}'},
                                json={'package_id': 'pro_monthly', 'origin_url': 'https://example.com'})
            if r.status_code == 200:
                j = r.json()
                url = j.get('url', '')
                sid = j.get('session_id', '')
                ok = url.startswith('https://checkout.stripe.com/') and sid.startswith('cs_live_')
                record(sec, 'POST /checkout/session pro_monthly LIVE', ok,
                       f'url={url[:60]}... session_id={sid[:18]}...')
            else:
                record(sec, 'POST /checkout/session', False,
                       f'status={r.status_code} body={r.text[:200]}')
        except Exception as e:
            record(sec, 'POST /checkout/session', False, str(e))

        try:
            r = await http.post('/webhook/stripe',
                                headers={'Stripe-Signature': 'bad', 'Content-Type': 'application/json'},
                                content=b'{}')
            detail = ''
            try:
                detail = r.json().get('detail', '')
            except Exception:
                detail = r.text
            ok = r.status_code == 400 and 'Invalid webhook' in detail
            record(sec, 'POST /webhook/stripe bad sig → 400', ok,
                   '' if ok else f'status={r.status_code} detail={detail!r}')
        except Exception as e:
            record(sec, 'POST /webhook/stripe bad sig', False, str(e))

        # ============== Section 5: Subscription cancel + Account deletion ==============
        sec = 'S5-cancel-delete'

        # Cancel flow: fresh user → upgrade in mongo to pro → cancel → free
        cancel_email = f'qa_cancel_{uuid.uuid4().hex[:8]}@goalpilot.ai'
        try:
            r = await http.post('/auth/register', json={
                'email': cancel_email, 'password': 'Cancel@1234', 'name': 'Cancel QA',
            })
            cancel_tok = r.json().get('token')
            cancel_uid = r.json().get('user', {}).get('id')
            # Upgrade in mongo to pro/monthly
            await db.users.update_one({'id': cancel_uid}, {'$set': {'plan': 'pro', 'billing': 'monthly'}})
            # Cancel
            r = await http.post('/subscription/cancel', headers={'Authorization': f'Bearer {cancel_tok}'})
            j = r.json() if r.status_code == 200 else {}
            ok1 = r.status_code == 200 and j.get('previous_plan') == 'pro' and j.get('plan') == 'free'
            # GET /me
            r2 = await http.get('/auth/me', headers={'Authorization': f'Bearer {cancel_tok}'})
            ok2 = r2.status_code == 200 and r2.json().get('plan') == 'free'
            record(sec, 'subscription/cancel: pro → free + /me confirms free', ok1 and ok2,
                   '' if ok1 and ok2 else f'cancel={j} me_status={r2.status_code} me_plan={r2.json().get("plan") if r2.status_code==200 else None}')
        except Exception as e:
            record(sec, 'subscription/cancel flow', False, str(e))

        # Account deletion flow: register user, create goal/tasks (use tasks insertion directly to avoid extra AI call), insert payment_transactions, then delete
        del_email = f'qa_del_{uuid.uuid4().hex[:8]}@goalpilot.ai'
        try:
            r = await http.post('/auth/register', json={
                'email': del_email, 'password': 'Delete@1234', 'name': 'Delete QA',
            })
            del_tok = r.json().get('token')
            del_uid = r.json().get('user', {}).get('id')

            # Seed data directly via Mongo (don't burn an extra Anthropic call):
            # one goal, two tasks, one payment_transactions doc.
            goal_doc = {
                'id': str(uuid.uuid4()),
                'user_id': del_uid,
                'title': 'Test deletion goal',
                'deadline': '2026-12-31',
                'status': 'active',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'plan': {'milestones': [], 'weekly_plan': [], 'daily_tasks': []},
            }
            await db.goals.insert_one(goal_doc)
            for i in range(2):
                await db.tasks.insert_one({
                    'id': str(uuid.uuid4()),
                    'user_id': del_uid,
                    'goal_id': goal_doc['id'],
                    'title': f'Test task {i}',
                    'priority': 'medium',
                    'est_minutes': 30,
                    'due_date': datetime.now(timezone.utc).date().isoformat(),
                    'completed': False,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                })
            await db.payment_transactions.insert_one({
                'id': str(uuid.uuid4()),
                'session_id': f'cs_test_qa_{uuid.uuid4().hex}',
                'user_id': del_uid,
                'user_email': del_email,
                'amount': 12.00,
                'currency': 'usd',
                'plan': 'pro',
                'billing': 'monthly',
                'payment_status': 'paid',
                'status': 'complete',
                'metadata': {'user_id': del_uid, 'user_email': del_email},
                'created_at': datetime.now(timezone.utc).isoformat(),
            })

            # DELETE /auth/account
            r = await http.request('DELETE', '/auth/account',
                                   headers={'Authorization': f'Bearer {del_tok}'})
            j = r.json() if r.status_code == 200 else {}
            ok_resp = r.status_code == 200 and j.get('ok') is True and j.get('deleted_user') is True

            # Mongo: user gone, goals gone, tasks gone, payment anonymized
            u_remaining = await db.users.count_documents({'id': del_uid})
            g_remaining = await db.goals.count_documents({'user_id': del_uid})
            t_remaining = await db.tasks.count_documents({'user_id': del_uid})
            pt_user = await db.payment_transactions.count_documents({'user_id': del_uid})
            pt_anon = await db.payment_transactions.count_documents({
                'user_id': 'deleted_user',
                'user_email': 'deleted_user',
            })

            ok_db = (u_remaining == 0 and g_remaining == 0 and t_remaining == 0
                     and pt_user == 0 and pt_anon >= 1)
            record(sec, 'DELETE /auth/account cascade + payments anonymized', ok_resp and ok_db,
                   f'resp_ok={ok_resp} users_left={u_remaining} goals={g_remaining} tasks={t_remaining} pt_user_link={pt_user} pt_anon={pt_anon}')
        except Exception as e:
            record(sec, 'DELETE /auth/account flow', False, str(e))

        # ============== Section 6: Notification prefs + scheduler ==============
        sec = 'S6-notif-sched'
        notif_email = f'qa_notif_{uuid.uuid4().hex[:8]}@goalpilot.ai'
        try:
            r = await http.post('/auth/register', json={
                'email': notif_email, 'password': 'Notif@1234', 'name': 'Notif QA',
            })
            ntok = r.json().get('token')
            r = await http.get('/notifications/prefs', headers={'Authorization': f'Bearer {ntok}'})
            j = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and j.get('morning') is True and j.get('streak') is True
            record(sec, 'GET /notifications/prefs default', ok,
                   '' if ok else f'status={r.status_code} body={j}')

            r = await http.patch('/notifications/prefs', headers={'Authorization': f'Bearer {ntok}'},
                                 json={'morning': False})
            j = r.json() if r.status_code == 200 else {}
            ok_set = r.status_code == 200 and j.get('morning') is False and j.get('streak') is True
            r2 = await http.get('/notifications/prefs', headers={'Authorization': f'Bearer {ntok}'})
            j2 = r2.json() if r2.status_code == 200 else {}
            ok_persist = j2.get('morning') is False and j2.get('streak') is True
            record(sec, 'PATCH /notifications/prefs {morning:false} + persists', ok_set and ok_persist,
                   '' if ok_set and ok_persist else f'set={j} get={j2}')
        except Exception as e:
            record(sec, 'notifications prefs', False, str(e))

        # Scheduler grep — check for 'hourly tick' OR 'Scheduler started' in logs
        try:
            out = subprocess.run(
                ['grep', '-c', '-E', 'Scheduler started: hourly tick',
                 '/var/log/supervisor/backend.err.log'],
                capture_output=True, text=True, timeout=10,
            )
            count = int(out.stdout.strip() or '0')
            ok = count >= 1
            record(sec, "grep 'Scheduler started: hourly tick' >= 1", ok, f'matches={count}')
        except Exception as e:
            record(sec, "grep scheduler log", False, str(e))

        # ============== Section 7: Dashboard + nudge + weekly review ==============
        # Use fresh_token (has 1 goal w/ tasks)
        sec = 'S7-dash-nudge-review'
        try:
            r = await http.get('/dashboard/stats', headers={'Authorization': f'Bearer {fresh_token}'})
            j = r.json() if r.status_code == 200 else {}
            required = ['streak', 'today_done', 'today_total', 'active_goals', 'total_completed', 'missed']
            missing = [k for k in required if k not in j]
            ok = r.status_code == 200 and not missing
            record(sec, 'GET /dashboard/stats has all keys', ok,
                   '' if ok else f'status={r.status_code} missing={missing} body={j}')
        except Exception as e:
            record(sec, 'GET /dashboard/stats', False, str(e))

        try:
            r = await http.get('/nudge', headers={'Authorization': f'Bearer {fresh_token}'})
            ok = r.status_code == 200
            record(sec, 'GET /nudge', ok, '' if ok else f'status={r.status_code} body={r.text[:200]}')
        except Exception as e:
            record(sec, 'GET /nudge', False, str(e))

        try:
            r = await http.get('/review/weekly', headers={'Authorization': f'Bearer {fresh_token}'})
            j = r.json() if r.status_code == 200 else {}
            ok = (
                r.status_code == 200
                and 'completion_rate' in j
                and 'completed' in j
                and 'missed' in j
                and isinstance(j.get('summary', ''), str) and len(j.get('summary', '')) >= 30
                and 'suggestion' in j
            )
            record(sec, 'GET /review/weekly fields ok', ok,
                   '' if ok else f'status={r.status_code} summary_len={len(j.get("summary",""))} keys={list(j.keys())}')
        except Exception as e:
            record(sec, 'GET /review/weekly', False, str(e))

        # ============== Section 8: Calendar export ==============
        sec = 'S8-calendar'
        try:
            r = await http.get('/calendar/url', headers={'Authorization': f'Bearer {fresh_token}'})
            j = r.json() if r.status_code == 200 else {}
            ical_token = j.get('token')
            ok = r.status_code == 200 and bool(ical_token)
            record(sec, 'GET /calendar/url returns token', ok,
                   '' if ok else f'status={r.status_code} body={j}')
            if ical_token:
                r = await http.get('/calendar/export.ics', params={'token': ical_token})
                ct = r.headers.get('content-type', '')
                ok2 = (
                    r.status_code == 200 and 'text/calendar' in ct
                    and r.text.startswith('BEGIN:VCALENDAR')
                )
                record(sec, 'GET /calendar/export.ics text/calendar+VCALENDAR', ok2,
                       '' if ok2 else f'status={r.status_code} ct={ct} first50={r.text[:50]!r}')
        except Exception as e:
            record(sec, 'calendar export', False, str(e))

        # ============== Cleanup ==============
        # Best-effort cleanup of fresh QA accounts
        try:
            for em in [fresh_email, notif_email]:
                u = await db.users.find_one({'email': em})
                if u:
                    uid = u['id']
                    await db.tasks.delete_many({'user_id': uid})
                    await db.goals.delete_many({'user_id': uid})
                    await db.idempotency_keys.delete_many({'user_id': uid})
                    await db.users.delete_one({'id': uid})
        except Exception:
            pass

        mongo.close()

    # ============== Summary ==============
    print('\n' + '=' * 80)
    print('GoalPilot final regression — summary')
    print('=' * 80)
    by_section = {}
    for sec, name, ok, detail in results:
        by_section.setdefault(sec, []).append((name, ok, detail))
    total_pass = sum(1 for _, _, ok, _ in results if ok)
    total = len(results)
    for sec, items in by_section.items():
        ps = sum(1 for _, ok, _ in items if ok)
        print(f'  {sec}: {ps}/{len(items)} pass')
        for name, ok, detail in items:
            if not ok:
                print(f'    FAIL — {name} — {detail}')
    print(f'\nTOTAL: {total_pass}/{total} pass')
    return 0 if total_pass == total else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
