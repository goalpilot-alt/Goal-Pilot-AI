"""
Backend test for Cancel Subscription and Account Deletion email features.
Tests against live preview backend. Uses httpx + motor directly.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

BASE = 'https://goal-pilot-ai.preview.emergentagent.com/api'
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'goalpilot_db')

results = []

def record(name: str, passed: bool, detail: str = ''):
    status = 'PASS' if passed else 'FAIL'
    results.append((name, passed, detail))
    print(f'[{status}] {name}  {detail}')


def unique_email(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:10]}@goalpilot.ai'


async def register(client: httpx.AsyncClient, prefix: str):
    email = unique_email(prefix)
    password = 'Test@1234'
    r = await client.post(f'{BASE}/auth/register', json={
        'email': email, 'password': password, 'name': f'{prefix.capitalize()} User',
    })
    assert r.status_code == 200, f'register failed {r.status_code} {r.text}'
    data = r.json()
    return data['token'], data['user'], email


async def main():
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo[DB_NAME]

    async with httpx.AsyncClient(timeout=180.0) as client:
        # ========= Section A: POST /api/subscription/cancel =========
        print('\n=== Section A: POST /api/subscription/cancel ===')

        # A.1: Auth required
        r = await client.post(f'{BASE}/subscription/cancel')
        record('A.1 no-auth -> 401', r.status_code == 401, f'status={r.status_code}')

        # A.2: Free user idempotent
        tok_free, user_free, email_free = await register(client, 'cancel_free')
        h = {'Authorization': f'Bearer {tok_free}'}
        r = await client.post(f'{BASE}/subscription/cancel', headers=h)
        body = r.json() if r.status_code == 200 else {}
        ok = (r.status_code == 200
              and body.get('ok') is True
              and body.get('plan') == 'free'
              and body.get('already_free') is True)
        record('A.2 free user cancel -> already_free:true', ok, f'status={r.status_code} body={body}')
        # /me still shows free
        r_me = await client.get(f'{BASE}/auth/me', headers=h)
        record('A.2 /me still plan=free', r_me.status_code == 200 and r_me.json().get('plan') == 'free',
               f'plan={r_me.json().get("plan")}')

        # A.3: Paid -> Free transition
        tok_pro, user_pro, email_pro = await register(client, 'cancel_pro')
        hp = {'Authorization': f'Bearer {tok_pro}'}
        # upgrade via Mongo
        await db.users.update_one(
            {'id': user_pro['id']},
            {'$set': {'plan': 'pro', 'billing': 'monthly', 'upgraded_at': datetime.now(timezone.utc).isoformat()}},
        )
        r_me = await client.get(f'{BASE}/auth/me', headers=hp)
        record('A.3c /me shows plan=pro', r_me.status_code == 200 and r_me.json().get('plan') == 'pro',
               f'plan={r_me.json().get("plan")}')

        r = await client.post(f'{BASE}/subscription/cancel', headers=hp)
        body = r.json() if r.status_code == 200 else {}
        ok = (r.status_code == 200
              and body.get('ok') is True
              and body.get('plan') == 'free'
              and body.get('previous_plan') == 'pro')
        record('A.3d paid cancel -> plan:free previous_plan:pro', ok, f'status={r.status_code} body={body}')

        # A.3e /me now free, Mongo doc check
        r_me = await client.get(f'{BASE}/auth/me', headers=hp)
        record('A.3e /me after cancel plan=free',
               r_me.status_code == 200 and r_me.json().get('plan') == 'free',
               f'plan={r_me.json().get("plan")}')

        doc = await db.users.find_one({'id': user_pro['id']})
        has_cancelled = 'cancelled_at' in doc
        has_prev = doc.get('previous_plan') == 'pro'
        billing_unset = 'billing' not in doc
        record('A.3e Mongo cancelled_at set', has_cancelled, f'cancelled_at={doc.get("cancelled_at")}')
        record('A.3e Mongo previous_plan=pro', has_prev, f'previous_plan={doc.get("previous_plan")}')
        record('A.3e Mongo billing unset', billing_unset, f'billing={doc.get("billing")}')

        # A.4: cancel-after-cancel idempotency
        r = await client.post(f'{BASE}/subscription/cancel', headers=hp)
        body = r.json() if r.status_code == 200 else {}
        ok = r.status_code == 200 and body.get('already_free') is True and body.get('plan') == 'free'
        record('A.4 second cancel -> already_free:true', ok, f'body={body}')

        # ========= Section B: DELETE /api/auth/account =========
        print('\n=== Section B: DELETE /api/auth/account ===')

        # B.1 auth required
        r = await client.delete(f'{BASE}/auth/account')
        record('B.1 no-auth -> 401', r.status_code == 401, f'status={r.status_code}')

        # B.2 successful deletion
        tok_del, user_del, email_del = await register(client, 'delete')
        hd = {'Authorization': f'Bearer {tok_del}'}
        uid_del = user_del['id']

        # Create a goal (to exercise cascade) — free plan allows 1 goal
        goal_payload = {
            'title': 'Learn Spanish A1',
            'motivation': 'Travel to Spain next year',
            'deadline': '2026-09-30',
            'hours_per_week': 5,
            'current_level': 'beginner',
        }
        r_goal = await client.post(f'{BASE}/goals', json=goal_payload, headers=hd)
        goal_created = r_goal.status_code == 200
        goal_id = r_goal.json().get('id') if goal_created else None
        record('B.2b goal created', goal_created, f'status={r_goal.status_code} goal_id={goal_id}')

        # Count tasks for user
        task_count_before = await db.tasks.count_documents({'user_id': uid_del})
        record('B.2b tasks exist for cascade test', task_count_before > 0, f'task_count={task_count_before}')

        # Insert fake payment_transactions doc
        fake_session_id = f'cs_test_anon_{uuid.uuid4().hex[:12]}'
        fake_tx_id = str(uuid.uuid4())
        await db.payment_transactions.insert_one({
            'id': fake_tx_id,
            'session_id': fake_session_id,
            'user_id': uid_del,
            'user_email': email_del,
            'package_id': 'pro_monthly',
            'plan': 'pro',
            'billing': 'monthly',
            'amount': 9.99,
            'currency': 'usd',
            'payment_status': 'paid',
            'status': 'complete',
            'metadata': {'user_id': uid_del, 'user_email': email_del},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        })

        # Insert a push_token for user
        await db.push_tokens.insert_one({
            'id': str(uuid.uuid4()),
            'user_id': uid_del,
            'token': 'ExponentPushToken[FAKE]',
            'created_at': datetime.now(timezone.utc).isoformat(),
        })
        # Insert an idempotency_keys row
        await db.idempotency_keys.insert_one({
            'user_id': uid_del,
            'key': 'fake_key',
            'status_code': 200,
            'response': {},
            'created_at': datetime.now(timezone.utc),
        })
        # Insert a push_log row
        await db.push_log.insert_one({
            'user_id': uid_del,
            'sent_at': datetime.now(timezone.utc).isoformat(),
            'message': 'test',
        })

        # DELETE account
        r = await client.delete(f'{BASE}/auth/account', headers=hd)
        body = r.json() if r.status_code == 200 else {}
        ok = r.status_code == 200 and body.get('ok') is True and body.get('deleted_user') is True
        record('B.2d DELETE /auth/account -> ok:true deleted_user:true', ok,
               f'status={r.status_code} body={body}')

        # Verify in Mongo
        users_gone = await db.users.find_one({'id': uid_del}) is None
        record('B.2e users doc gone', users_gone)
        goals_gone = await db.goals.count_documents({'user_id': uid_del}) == 0
        record('B.2e goals cascade-deleted', goals_gone)
        tasks_gone = await db.tasks.count_documents({'user_id': uid_del}) == 0
        record('B.2e tasks cascade-deleted', tasks_gone)
        push_tok_gone = await db.push_tokens.count_documents({'user_id': uid_del}) == 0
        record('B.2e push_tokens gone', push_tok_gone)
        idem_gone = await db.idempotency_keys.count_documents({'user_id': uid_del}) == 0
        record('B.2e idempotency_keys gone', idem_gone)
        push_log_gone = await db.push_log.count_documents({'user_id': uid_del}) == 0
        record('B.2e push_log gone', push_log_gone)

        # Verify payment_transactions anonymized
        tx = await db.payment_transactions.find_one({'session_id': fake_session_id})
        tx_exists = tx is not None
        anon_ok = (tx_exists
                   and tx.get('user_id') == 'deleted_user'
                   and tx.get('user_email') == 'deleted_user'
                   and 'anonymized_at' in tx)
        record('B.2f payment_transactions anonymized', anon_ok,
               f'user_id={tx.get("user_id") if tx_exists else None} user_email={tx.get("user_email") if tx_exists else None} anon_at={tx.get("anonymized_at") if tx_exists else None}')

        # B.2g: /me with deleted token should NOT be 200
        r_me = await client.get(f'{BASE}/auth/me', headers=hd)
        record('B.2g /me with deleted user token != 200',
               r_me.status_code != 200, f'status={r_me.status_code}')

        # Clean up anonymized payment tx (best-effort)
        await db.payment_transactions.delete_one({'session_id': fake_session_id})

        # ========= Section C: Regression smoke =========
        print('\n=== Section C: Regression smoke ===')
        email_smoke = unique_email('smoke')
        pw = 'Test@1234'
        r = await client.post(f'{BASE}/auth/register', json={
            'email': email_smoke, 'password': pw, 'name': 'Smoke Tester',
        })
        record('C register', r.status_code == 200, f'status={r.status_code}')
        tok_smoke = r.json().get('token')

        r = await client.post(f'{BASE}/auth/login', json={'email': email_smoke, 'password': pw})
        record('C login', r.status_code == 200 and r.json().get('token'), f'status={r.status_code}')

        hs = {'Authorization': f'Bearer {tok_smoke}'}
        r = await client.get(f'{BASE}/auth/me', headers=hs)
        record('C /auth/me', r.status_code == 200 and r.json().get('email') == email_smoke,
               f'status={r.status_code}')

        r = await client.post(f'{BASE}/checkout/session', headers=hs, json={
            'package_id': 'pro_monthly',
            'origin_url': 'https://example.com',
        })
        cs_body = r.json() if r.status_code == 200 else {}
        sid = cs_body.get('session_id', '')
        ok = r.status_code == 200 and bool(cs_body.get('url')) and sid.startswith('cs_live_')
        record('C /checkout/session pro_monthly returns cs_live_...',
               ok, f'status={r.status_code} session_id={sid[:25]}...')

    mongo.close()

    # Summary
    print('\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    for name, p, d in results:
        print(f'  [{"OK" if p else "XX"}] {name}')
    print(f'\n{passed}/{total} assertions passed')
    return passed, total


if __name__ == '__main__':
    asyncio.run(main())
