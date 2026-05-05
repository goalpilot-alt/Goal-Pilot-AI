from datetime import datetime, timezone
from typing import List
from fastapi.responses import Response


def build_ics(tasks: List[dict], goals: List[dict]) -> Response:
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//GoalPilot AI//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:GoalPilot AI',
    ]
    now_stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

    for t in tasks:
        due = t.get('due_date', '')
        if not due:
            continue
        dt = due.replace('-', '')
        uid = f"task-{t['id']}@goalpilot.ai"
        summary = (t.get('title') or 'Task').replace('\n', ' ')
        lines += [
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{now_stamp}',
            f'DTSTART;VALUE=DATE:{dt}',
            f'DTEND;VALUE=DATE:{dt}',
            f'SUMMARY:{summary}',
            f"DESCRIPTION:Priority: {t.get('priority','')} | {t.get('est_minutes',0)} min",
            'END:VEVENT',
        ]

    for g in goals:
        deadline = g.get('deadline', '')
        if not deadline:
            continue
        dt = deadline.replace('-', '')
        uid = f"goal-{g['id']}@goalpilot.ai"
        summary = f"GOAL DEADLINE: {g.get('title','')}"
        lines += [
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{now_stamp}',
            f'DTSTART;VALUE=DATE:{dt}',
            f'DTEND;VALUE=DATE:{dt}',
            f'SUMMARY:{summary}',
            'END:VEVENT',
        ]

    lines.append('END:VCALENDAR')
    body = '\r\n'.join(lines)
    return Response(content=body, media_type='text/calendar; charset=utf-8')
