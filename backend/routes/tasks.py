from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.db import db
from models.schemas import TaskToggleReq

router = APIRouter()


@router.get('/tasks/today')
async def tasks_today(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date().isoformat()
    cursor = db.tasks.find({'user_id': user['id'], 'due_date': today}, {'_id': 0}).sort('priority', 1)
    return await cursor.to_list(200)


@router.get('/tasks/missed')
async def tasks_missed(user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date().isoformat()
    cursor = db.tasks.find({
        'user_id': user['id'],
        'due_date': {'$lt': today},
        'completed': False,
    }, {'_id': 0}).sort('due_date', -1).limit(20)
    return await cursor.to_list(20)


@router.get('/tasks')
async def list_tasks(goal_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {'user_id': user['id']}
    if goal_id:
        q['goal_id'] = goal_id
    cursor = db.tasks.find(q, {'_id': 0}).sort('due_date', 1)
    return await cursor.to_list(500)


@router.patch('/tasks/{task_id}')
async def toggle_task(task_id: str, req: TaskToggleReq, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat() if req.completed else None
    res = await db.tasks.update_one(
        {'id': task_id, 'user_id': user['id']},
        {'$set': {'completed': req.completed, 'completed_at': now}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail='Task not found')
    task = await db.tasks.find_one({'id': task_id}, {'_id': 0})
    return task
