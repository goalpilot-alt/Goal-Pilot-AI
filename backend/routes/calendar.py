import jwt
from fastapi import APIRouter, Depends, HTTPException

from core.auth import create_access_token, get_current_user
from core.config import JWT_SECRET, JWT_ALGO
from core.db import db
from services.calendar_ics import build_ics

router = APIRouter()


@router.get('/calendar/export.ics')
async def calendar_ics(token: str):
    """Return .ics file. Auth via query token because calendar apps can't send headers."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = payload['sub']
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')

    tasks = await db.tasks.find({'user_id': user_id}, {'_id': 0}).to_list(500)
    goals = await db.goals.find({'user_id': user_id}, {'_id': 0}).to_list(50)
    return build_ics(tasks, goals)


@router.get('/calendar/url')
async def calendar_url(user: dict = Depends(get_current_user)):
    token = create_access_token(user['id'], user['email'])
    return {'token': token}
