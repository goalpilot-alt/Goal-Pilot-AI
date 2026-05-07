import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from core.auth import (
    create_access_token, get_current_user, hash_password, verify_password,
)
from core.config import SUPPORTED_LOCALES
from core.db import db
from models.schemas import RegisterReq, LoginReq, AuthResp, LocaleReq, TimezoneReq

router = APIRouter()


@router.post('/auth/register', response_model=AuthResp)
async def register(req: RegisterReq):
    email = req.email.lower()
    existing = await db.users.find_one({'email': email})
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    user_id = str(uuid.uuid4())
    user_doc = {
        'id': user_id,
        'email': email,
        'name': req.name,
        'password_hash': hash_password(req.password),
        'plan': 'free',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(user_id, email)
    user_out = {k: v for k, v in user_doc.items() if k not in ('_id', 'password_hash')}
    return {'token': token, 'user': user_out}


@router.post('/auth/login', response_model=AuthResp)
async def login(req: LoginReq):
    email = req.email.lower()
    user = await db.users.find_one({'email': email})
    if not user or not verify_password(req.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    token = create_access_token(user['id'], email)
    user_out = {k: v for k, v in user.items() if k not in ('_id', 'password_hash')}
    return {'token': token, 'user': user_out}


@router.get('/auth/me')
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post('/auth/locale')
async def set_locale(req: LocaleReq, user: dict = Depends(get_current_user)):
    if req.locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail='Unsupported locale')
    await db.users.update_one({'id': user['id']}, {'$set': {'locale': req.locale}})
    return {'ok': True, 'locale': req.locale}


@router.post('/auth/timezone')
async def set_timezone(req: TimezoneReq, user: dict = Depends(get_current_user)):
    """Save the user's IANA timezone (e.g. 'America/New_York'). Validated against zoneinfo."""
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        ZoneInfo(req.timezone)  # raises if invalid
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid timezone')
    await db.users.update_one({'id': user['id']}, {'$set': {'timezone': req.timezone}})
    return {'ok': True, 'timezone': req.timezone}


@router.delete('/auth/account')
async def delete_account(user: dict = Depends(get_current_user)):
    """Hard-delete the user and all owned data.

    payment_transactions are kept (legally required for accounting) but anonymized:
    user_id and user_email are scrubbed to 'deleted_user'.
    """
    uid = user['id']
    # Anonymize payment records (required for accounting/tax)
    await db.payment_transactions.update_many(
        {'user_id': uid},
        {'$set': {
            'user_id': 'deleted_user',
            'user_email': 'deleted_user',
            'metadata.user_id': 'deleted_user',
            'metadata.user_email': 'deleted_user',
            'anonymized_at': datetime.now(timezone.utc).isoformat(),
        }},
    )
    # Hard-delete everything else owned by the user
    await db.tasks.delete_many({'user_id': uid})
    await db.goals.delete_many({'user_id': uid})
    await db.push_tokens.delete_many({'user_id': uid})
    await db.idempotency_keys.delete_many({'user_id': uid})
    await db.push_log.delete_many({'user_id': uid})
    res = await db.users.delete_one({'id': uid})
    return {'ok': True, 'deleted_user': res.deleted_count == 1}
