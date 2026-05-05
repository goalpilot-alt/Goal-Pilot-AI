from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.db import db
from models.schemas import PushTokenReq

router = APIRouter()


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
