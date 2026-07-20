from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'goalpilot')
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-me-in-prod')
JWT_ALGO = 'HS256'
# Optional — only used as a legacy fallback in ai.py. Safe to leave empty.
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Server-side plan catalog — NEVER trust amounts from client
PACKAGES = {
    'pro_monthly':    {'plan': 'pro',   'billing': 'monthly', 'amount': 12.00,  'currency': 'usd'},
    'pro_annual':     {'plan': 'pro',   'billing': 'annual',  'amount': 108.00, 'currency': 'usd'},
    'coach_monthly':  {'plan': 'coach', 'billing': 'monthly', 'amount': 29.00,  'currency': 'usd'},
    'coach_annual':   {'plan': 'coach', 'billing': 'annual',  'amount': 252.00, 'currency': 'usd'},
}

PLAN_GOAL_LIMITS = {'free': 1, 'pro': 5, 'coach': None}

SUPPORTED_LOCALES = {'en-US', 'en-GB', 'es', 'fr', 'cs', 'sk', 'ru', 'zh-CN'}

LOCALE_LANGUAGE_NAMES = {
    'en-US': 'English (US)',
    'en-GB': 'English (UK)',
    'es':    'Spanish (Español)',
    'fr':    'French (Français)',
    'cs':    'Czech (Čeština)',
    'sk':    'Slovak (Slovenčina)',
    'ru':    'Russian (Русский)',
    'zh-CN': 'Simplified Chinese (中文 简体)',
}

# Daily push schedule (UTC). Default 09:00 UTC = 4am ET / 5am CET.
PUSH_DAILY_HOUR_UTC = int(os.environ.get('PUSH_DAILY_HOUR_UTC', '9'))
PUSH_DAILY_MINUTE_UTC = int(os.environ.get('PUSH_DAILY_MINUTE_UTC', '0'))
