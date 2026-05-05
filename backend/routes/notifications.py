from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.db import db
from models.schemas import PushTokenReq, NotifPrefsReq

router = APIRouter()

DEFAULT_PREFS = {'morning': True, 'streak': True}


def _normalize_prefs(raw) -> dict:
    if not isinstance(raw, dict):
        return DEFAULT_PREFS.copy()
    return {
        'morning': bool(raw.get('morning', True)),
        'streak':  bool(raw.get('streak', True)),
    }


@router.get('/notifications/prefs')
async def get_notif_prefs(user: dict = Depends(get_current_user)):
    return _normalize_prefs(user.get('notification_prefs'))


@router.patch('/notifications/prefs')
async def update_notif_prefs(req: NotifPrefsReq, user: dict = Depends(get_current_user)):
    current = _normalize_prefs(user.get('notification_prefs'))
    if req.morning is not None:
        current['morning'] = bool(req.morning)
    if req.streak is not None:
        current['streak'] = bool(req.streak)
    await db.users.update_one({'id': user['id']}, {'$set': {'notification_prefs': current}})
    return current


@router.post('/notifications/token')
async def save_push_token(req: PushTokenReq, user: dict = Depends(get_current_user)):
    if not req.token:
        raise HTTPException(status_code=400, detail='Missing token')
    await db.push_tokens.update_one(
        {'user_id': user['id'], 'token': req.token},
        {'$set': {
            'user_id': user['id'],
            'token': req.token,
            'platform': req.platform or 'unknown',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {'ok': True}


@router.delete('/notifications/token')
async def remove_push_token(token: str, user: dict = Depends(get_current_user)):
    await db.push_tokens.delete_one({'user_id': user['id'], 'token': token})
    return {'ok': True}
