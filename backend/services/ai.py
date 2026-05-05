import json
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage
from core.config import EMERGENT_LLM_KEY, LOCALE_LANGUAGE_NAMES

logger = logging.getLogger(__name__)


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


async def generate_ai_plan(goal: dict, locale: str = 'en-US') -> dict:
    session_id = f"goal-{goal['id']}"
    system_msg = (
        'You are GoalPilot AI, an expert coach and planner. '
        'You receive a user goal and produce a structured JSON plan. '
        'Be specific, motivating and realistic. Return ONLY valid JSON, no markdown. '
        + lang_instruction(locale)
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_msg,
    ).with_model('anthropic', 'claude-sonnet-4-5-20250929')

    prompt = f"""Create a practical plan for this goal.

Goal: {goal['title']}
Deadline: {goal['deadline']}
Motivation: {goal['motivation']}
Current level: {goal['current_level']}
Time per week: {goal['hours_per_week']} hours

Return JSON with this EXACT shape:
{{
  "summary": "2-3 sentence inspiring summary of the plan",
  "why_it_works": "Short paragraph on why this plan leads to success",
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

Create 3-5 milestones, 4 weeks of weekly_plan, and 5-7 daily_tasks starting day_offset 0 (today).
"""
    response = await chat.send_message(UserMessage(text=prompt))
    text = _strip_fences(response)
    try:
        return json.loads(text)
    except Exception as e:
        logger.error(f'AI parse error: {e}\nRaw: {text[:500]}')
        return {
            'summary': 'Your AI plan is being prepared. Keep going!',
            'why_it_works': 'Consistent small actions compound into results.',
            'milestones': [],
            'weekly_plan': [],
            'daily_tasks': [],
        }


async def generate_weekly_review(user_id: str, locale: str, completed: int, missed: int, total_due: int, goal_titles: str, today_s: str):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f'review-{user_id}-{today_s}',
            system_message='You are an AI accountability coach. Be warm, specific, motivating. Return ONLY JSON. ' + lang_instruction(locale),
        ).with_model('anthropic', 'claude-sonnet-4-5-20250929')
        prompt = f"""User progress last 7 days:
- Tasks completed: {completed}
- Tasks missed: {missed}
- Total tasks due: {total_due}
- Active goals: {goal_titles}

Return JSON:
{{\"summary\": \"2-3 sentences celebrating wins & acknowledging misses\", \"suggestion\": \"1 specific actionable focus for next week\"}}"""
        resp = await chat.send_message(UserMessage(text=prompt))
        text = _strip_fences(resp)
        parsed = json.loads(text)
        return parsed.get('summary', ''), parsed.get('suggestion', '')
    except Exception as e:
        logger.error(f'Review AI failed: {e}')
        return (
            f'This week you completed {completed} tasks. Keep building momentum!',
            'Focus on finishing your top priority task each morning.',
        )
