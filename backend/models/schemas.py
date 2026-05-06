from typing import Optional
from pydantic import BaseModel, EmailStr


class RegisterReq(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class AuthResp(BaseModel):
    token: str
    user: dict


class GoalCreateReq(BaseModel):
    title: str
    deadline: str  # ISO date
    motivation: str
    current_level: str  # beginner/intermediate/advanced
    hours_per_week: int


class TaskToggleReq(BaseModel):
    completed: bool


class CheckoutSessionReq(BaseModel):
    package_id: str
    origin_url: str


class PushTokenReq(BaseModel):
    token: str
    platform: Optional[str] = None  # 'ios' | 'android' | 'web'


class NotifPrefsReq(BaseModel):
    morning: Optional[bool] = None
    streak: Optional[bool] = None


class LocaleReq(BaseModel):
    locale: str


class TimezoneReq(BaseModel):
    timezone: str  # IANA name e.g. "America/New_York"
