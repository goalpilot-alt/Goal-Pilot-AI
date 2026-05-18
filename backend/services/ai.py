"""AI plan generation service.

Prefers a direct Anthropic SDK call when ANTHROPIC_API_KEY is set (no proxy budget cap).
Falls back to emergentintegrations LlmChat (Emergent universal key proxy) otherwise.
"""
import json
import logging
import os
from datetime import datetime, timezone, date

from core.config import EMERGENT_LLM_KEY, LOCALE_LANGUAGE_NAMES

logger = logging.getLogger(__name__)

ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '').strip()
ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-5-20250929')


def lang_instruction(locale: str) -> str:
    name = LOCALE_LANGUAGE_NAMES.get(locale, 'English (US)')
    return f'Respond entirely in {name}. All field values in the JSON must be written in {name}.'


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
        text = text.strip()
    return text


def _days_between(start_iso: str, end_iso: str) -> int:
    try:
        s = date.fromisoformat(start_iso)
        e = date.fromisoformat(end_iso)
        return (e - s).days
    except Exception:
        return 0


async def _llm_complete(system_msg: str, prompt: str, session_id: str, max_tokens: int = 4096) -> str:
    """Run the LLM. Prefer direct Anthropic SDK; fallback to Emergent proxy.

    Raises on failure so callers can surface a clear error to the user.
    """
    if ANTHROPIC_KEY:
        # Direct Anthropic SDK call (async)
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_KEY)
        msg = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_msg,
            messages=[{'role': 'user', 'content': prompt}],
        )
        # msg.content is a list of content blocks; concat text
        parts = []
        for block in msg.content:
            text = getattr(block, 'text', None)
            if text:
                parts.append(text)
        return ''.join(parts)

    # Fallback to emergent proxy
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_msg,
    ).with_model('anthropic', ANTHROPIC_MODEL)
    return await chat.send_message(UserMessage(text=prompt))


async def generate_ai_plan(goal: dict, locale: str = 'en-US') -> dict:
    session_id = f"goal-{goal['id']}"
    today_iso = datetime.now(timezone.utc).date().isoformat()
    days_available = max(0, _days_between(today_iso, goal['deadline']))
    weeks_available = max(1, days_available // 7)

    system_msg = (
        'You are GoalPilot AI, an expert coach and planner. '
        'You receive a user goal with a START DATE (today) and DEADLINE. '
        'You MUST design the entire plan to fit between START DATE and DEADLINE. '
        'Be specific, motivating and realistic. Return ONLY valid JSON, no markdown. '
        + lang_instruction(locale)
    )

    prompt = f"""Create a practical plan for this goal.

START DATE (today): {today_iso}
DEADLINE: {goal['deadline']}
DAYS AVAILABLE: {days_available} days (~{weeks_available} weeks)
Goal: {goal['title']}
Motivation: {goal['motivation']}
Current level: {goal['current_level']}
Time per week: {goal['hours_per_week']} hours

CRITICAL CONSTRAINTS:
1. ALL milestone target_date values MUST be between {today_iso} and {goal['deadline']} (inclusive).
2. weekly_plan MUST have AT MOST 12 entries. If the goal spans more than 12 weeks, GROUP the remaining weeks into thematic phases (e.g. "Weeks 13-20: Consolidation") and emit a maximum of 12 phase entries — NEVER emit one entry per week beyond 12.
3. daily_tasks day_offset values MUST satisfy 0 <= day_offset <= {days_available}.
4. Assess feasibility: given the user's level, hours_per_week and days_available, is the goal realistically achievable?
   - "ok": plenty of time
   - "tight": doable but stretched, will need discipline
   - "unrealistic": clearly too short to achieve at this hours_per_week & level
5. If "tight" or "unrealistic", set suggested_deadline_iso to a realistic YYYY-MM-DD date (in the future, after today). Otherwise set it to the original DEADLINE.

Return JSON with this EXACT shape:
{{
  "summary": "2-3 sentence inspiring summary that mentions the actual time-frame (e.g. 'In the next {weeks_available} weeks...')",
  "why_it_works": "Short paragraph explaining why the plan fits the available time",
  "feasibility": "ok|tight|unrealistic",
  "feasibility_reason": "1-2 sentences explaining the feasibility judgement (mention hours_per_week, level, time-frame)",
  "suggested_deadline_iso": "YYYY-MM-DD",
  "suggested_weeks": <integer total weeks recommended>,
  "milestones": [
    {{"title": "Milestone name", "target_date": "YYYY-MM-DD", "description": "what they will achieve"}}
  ],
  "weekly_plan": [
    {{"week": 1, "focus": "theme", "goals": ["...", "..."]}}
  ],
  "daily_tasks": [
    {{"title": "Task name", "priority": "high|medium|low", "est_minutes": 30, "day_offset": 0}}
  ]
}}

Generate 3-5 milestones spread across the {weeks_available} weeks (do not stack them all at the end).
Generate AT MOST 12 weekly_plan items. If the goal spans more than 12 weeks, group later weeks into phases (e.g. "Weeks 13-26: Practice & consolidation"). NEVER exceed 12 items.
Generate 5-7 daily_tasks starting day_offset 0 (today).
"""
    response = await _llm_complete(system_msg, prompt, session_id, max_tokens=16000)
    text = _strip_fences(response)
    try:
        plan = json.loads(text)
    except Exception as e:
        logger.error(f'AI parse error: {e}\nRaw: {text[:500]}')
        # Re-raise so caller surfaces a clear 503 to the user instead of empty stub
        raise RuntimeError('AI returned malformed JSON') from e

    # Validate the plan actually has content (defend against the silent-empty bug)
    milestones = plan.get('milestones') or []
    weekly_plan = plan.get('weekly_plan') or []
    daily_tasks = plan.get('daily_tasks') or []
    if not milestones and not weekly_plan and not daily_tasks:
        raise RuntimeError('AI returned an empty plan (no milestones/weeks/tasks)')

    plan.setdefault('feasibility', 'ok')
    plan.setdefault('suggested_deadline_iso', goal['deadline'])
    plan.setdefault('feasibility_reason', '')
    return plan


async def generate_weekly_review(user_id: str, locale: str, completed: int, missed: int, total_due: int, goal_titles: str, today_s: str):
    try:
        system_msg = 'You are an AI accountability coach. Be warm, specific, motivating. Return ONLY JSON. ' + lang_instruction(locale)
        prompt = f"""User progress last 7 days:
- Tasks completed: {completed}
- Tasks missed: {missed}
- Total tasks due: {total_due}
- Active goals: {goal_titles}

Return JSON:
{{\"summary\": \"2-3 sentences celebrating wins & acknowledging misses\", \"suggestion\": \"1 specific actionable focus for next week\"}}"""
        resp = await _llm_complete(system_msg, prompt, f'review-{user_id}-{today_s}', max_tokens=512)
        text = _strip_fences(resp)
        parsed = json.loads(text)
        return parsed.get('summary', ''), parsed.get('suggestion', '')
    except Exception as e:
        logger.error(f'Review AI failed: {e}')
        return (
            f'This week you completed {completed} tasks. Keep building momentum!',
            'Focus on finishing your top priority task each morning.',
        )
