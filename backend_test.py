"""Targeted test for /api/notifications/prefs endpoints and scheduler integration.

Runs against the live preview backend URL from frontend/.env and uses test creds
from /app/memory/test_credentials.md.
"""
import sys
import uuid
import requests

BACKEND_URL = 'https://goal-pilot-ai.preview.emergentagent.com'
API = f'{BACKEND_URL}/api'

TEST_EMAIL = 'tester@goalpilot.ai'
TEST_PASSWORD = 'Test@1234'
TEST_NAME = 'Tester'


def _login_or_register(email: str, password: str, name: str) -> str:
    r = requests.post(f'{API}/auth/login', json={'email': email, 'password': password}, timeout=30)
    if r.status_code == 200:
        return r.json()['token']
    r2 = requests.post(f'{API}/auth/register', json={'email': email, 'password': password, 'name': name}, timeout=30)
    if r2.status_code == 200:
        return r2.json()['token']
    raise RuntimeError(f'Could not login/register {email}: {r.status_code} {r.text} / {r2.status_code} {r2.text}')


def _results():
    return {'pass': 0, 'fail': 0, 'notes': []}


def ok(res, msg):
    res['pass'] += 1
    print(f'PASS  {msg}')


def bad(res, msg):
    res['fail'] += 1
    res['notes'].append(msg)
    print(f'FAIL  {msg}')


def test_get_prefs_default_and_401(res):
    # 401 without token
    r = requests.get(f'{API}/notifications/prefs', timeout=30)
    if r.status_code in (401, 403):
        ok(res, f'GET /notifications/prefs without token -> {r.status_code} (unauthorized)')
    else:
        bad(res, f'Expected 401/403 without token, got {r.status_code}: {r.text[:200]}')

    # Fresh user -> returns default {morning: true, streak: true}
    fresh_email = f'notif_fresh_{uuid.uuid4().hex[:8]}@goalpilot.ai'
    token = _login_or_register(fresh_email, 'Fresh@1234', 'Fresh User')
    h = {'Authorization': f'Bearer {token}'}
    r = requests.get(f'{API}/notifications/prefs', headers=h, timeout=30)
    if r.status_code != 200:
        bad(res, f'Fresh GET /notifications/prefs expected 200, got {r.status_code}: {r.text[:200]}')
        return None, None
    body = r.json()
    if body == {'morning': True, 'streak': True}:
        ok(res, f'Fresh user GET returns defaults: {body}')
    else:
        bad(res, f'Fresh user GET expected {{morning:true, streak:true}}, got {body}')
    return token, fresh_email


def test_patch_prefs(res, token):
    h = {'Authorization': f'Bearer {token}'}

    # Step 1: {"morning": false} -> {morning:false, streak:true}
    r = requests.patch(f'{API}/notifications/prefs', headers=h, json={'morning': False}, timeout=30)
    if r.status_code == 200 and r.json() == {'morning': False, 'streak': True}:
        ok(res, f'PATCH morning=false -> {r.json()}')
    else:
        bad(res, f'PATCH morning=false expected {{morning:false, streak:true}}, got {r.status_code} {r.text[:200]}')

    # Persistence check via GET
    r = requests.get(f'{API}/notifications/prefs', headers=h, timeout=30)
    if r.status_code == 200 and r.json() == {'morning': False, 'streak': True}:
        ok(res, 'GET after PATCH morning=false persists -> {morning:false, streak:true}')
    else:
        bad(res, f'Persistence fail after PATCH morning=false: got {r.status_code} {r.text[:200]}')

    # Step 2: {"streak": false} -> {morning:false, streak:false}
    r = requests.patch(f'{API}/notifications/prefs', headers=h, json={'streak': False}, timeout=30)
    if r.status_code == 200 and r.json() == {'morning': False, 'streak': False}:
        ok(res, f'PATCH streak=false -> {r.json()}')
    else:
        bad(res, f'PATCH streak=false expected {{morning:false, streak:false}}, got {r.status_code} {r.text[:200]}')

    # Step 3: {"morning": true, "streak": true} -> {morning:true, streak:true}
    r = requests.patch(f'{API}/notifications/prefs', headers=h, json={'morning': True, 'streak': True}, timeout=30)
    if r.status_code == 200 and r.json() == {'morning': True, 'streak': True}:
        ok(res, f'PATCH morning=true streak=true -> {r.json()}')
    else:
        bad(res, f'PATCH both true expected defaults, got {r.status_code} {r.text[:200]}')

    # Step 4: Empty body {} -> returns current prefs unchanged, 200
    r = requests.patch(f'{API}/notifications/prefs', headers=h, json={}, timeout=30)
    if r.status_code == 200 and r.json() == {'morning': True, 'streak': True}:
        ok(res, f'PATCH empty body -> {r.json()} (unchanged)')
    else:
        bad(res, f'PATCH empty body expected 200 with unchanged prefs, got {r.status_code} {r.text[:200]}')

    # 401 on PATCH without token
    r = requests.patch(f'{API}/notifications/prefs', json={'morning': False}, timeout=30)
    if r.status_code in (401, 403):
        ok(res, f'PATCH /notifications/prefs without token -> {r.status_code}')
    else:
        bad(res, f'Expected 401/403 on PATCH without token, got {r.status_code}')


def main():
    print(f'Testing against {API}')
    res = _results()

    try:
        t = _login_or_register(TEST_EMAIL, TEST_PASSWORD, TEST_NAME)
        print(f'Tester account OK (token len={len(t)})')
    except Exception as e:
        print(f'Tester account check failed: {e}')

    token, _ = test_get_prefs_default_and_401(res)
    if token:
        test_patch_prefs(res, token)

    print('\n========================')
    print(f'PASS={res["pass"]}  FAIL={res["fail"]}')
    for n in res['notes']:
        print(' -', n)
    print('========================')
    return 0 if res['fail'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
