"""GoalPilot AI — FastAPI entry point.

Modular layout:
  core/      -> config, db, auth helpers
  models/    -> pydantic schemas
  services/  -> ai, push, scheduler, stripe, calendar
  routes/    -> auth, goals, tasks, dashboard, nudge, checkout, calendar, notifications
"""
import logging
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

# Loads .env via core.config import-time
from core.db import client, db  # noqa: F401
from routes import auth, goals, tasks, dashboard, nudge, checkout, calendar, notifications
from services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
api = APIRouter(prefix='/api')

# Mount feature routers
api.include_router(auth.router)
api.include_router(goals.router)
api.include_router(tasks.router)
api.include_router(dashboard.router)
api.include_router(nudge.router)
api.include_router(checkout.router)
api.include_router(calendar.router)
api.include_router(notifications.router)


@api.get('/')
async def root():
    return {'app': 'GoalPilot AI', 'status': 'ok'}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
async def on_start():
    await db.users.create_index('email', unique=True)
    await db.goals.create_index('user_id')
    await db.tasks.create_index([('user_id', 1), ('due_date', 1)])
    await db.idempotency_keys.create_index([('user_id', 1), ('key', 1)], unique=True)
    await db.idempotency_keys.create_index('created_at', expireAfterSeconds=60 * 60 * 26)  # 26h TTL
    # Start daily push scheduler
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f'Scheduler failed to start: {e}')


@app.on_event('shutdown')
async def on_shutdown():
    try:
        stop_scheduler()
    except Exception:
        pass
    client.close()
