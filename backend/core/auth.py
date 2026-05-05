import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import JWT_SECRET, JWT_ALGO
from .db import db

security = HTTPBearer(auto_error=False)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        'sub': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(days=7),
        'type': 'access',
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail='Not authenticated')
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        user = await db.users.find_one({'id': payload['sub']}, {'_id': 0, 'password_hash': 0})
        if not user:
            raise HTTPException(status_code=401, detail='User not found')
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expired')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')


async def get_user_locale(user: dict) -> str:
    from .config import SUPPORTED_LOCALES
    loc = user.get('locale') or 'en-US'
    return loc if loc in SUPPORTED_LOCALES else 'en-US'
