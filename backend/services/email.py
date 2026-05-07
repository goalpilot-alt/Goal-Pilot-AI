"""Resend email dispatcher.

Lightweight wrapper around Resend's HTTPS API: https://resend.com/docs/api-reference
No SDK needed \u2014 plain httpx POST. Fail-soft: never raises out of the email path.
"""
import logging
import os
import httpx

logger = logging.getLogger(__name__)

RESEND_URL = 'https://api.resend.com/emails'


def _api_key() -> str:
    return os.environ.get('RESEND_API_KEY', '')


def _from_addr() -> str:
    # Default to Resend's safe sandbox sender so the call works even before the user verifies a domain
    return os.environ.get('EMAIL_FROM', 'GoalPilot <onboarding@resend.dev>')


async def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    api = _api_key()
    if not api:
        logger.warning('Resend not configured \u2014 email skipped')
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload: dict = {
                'from': _from_addr(),
                'to': [to],
                'subject': subject,
                'html': html,
            }
            if text:
                payload['text'] = text
            r = await client.post(
                RESEND_URL,
                headers={
                    'Authorization': f'Bearer {api}',
                    'Content-Type': 'application/json',
                },
                json=payload,
            )
            if r.status_code in (200, 202):
                logger.info(f'Email sent to {to}: subject={subject}')
                return True
            logger.error(f'Resend send failed: {r.status_code} body={r.text[:200]}')
            return False
    except Exception as e:
        logger.error(f'Resend send exception: {e}')
        return False


async def send_account_deleted_email(to: str, name: str | None = None) -> bool:
    safe_name = (name or '').strip() or 'there'
    subject = 'Your GoalPilot account has been deleted'
    html = f"""\
<div style=\"font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:560px;margin:0 auto;color:#0f172a\">
  <h1 style=\"color:#FF5E00;font-size:22px;margin-bottom:0\">Account deleted</h1>
  <p>Hi {safe_name},</p>
  <p>This email confirms your <strong>GoalPilot</strong> account and all associated data
  (goals, tasks, notification tokens, AI plans) were permanently deleted.</p>
  <p>For tax and accounting purposes (Czech law), payment records are kept for up to 10 years but have been
  anonymised \u2014 they no longer link to your identity.</p>
  <p>If you didn't request this, please reply immediately to <a href=\"mailto:goalpilot@goal-pilot.com\">goalpilot@goal-pilot.com</a>.</p>
  <p>Thanks for trying GoalPilot. We're sorry to see you go and wish you success on your goals \u2014 in any tool you choose.</p>
  <p style=\"color:#64748b;font-size:12px;margin-top:32px\">GoalPilot \u2022 goalpilot@goal-pilot.com</p>
</div>"""
    text = (
        f"Hi {safe_name},\n\n"
        "This email confirms your GoalPilot account and all associated data were permanently deleted.\n\n"
        "Payment records are kept anonymised for 10 years (Czech tax law).\n\n"
        "If you didn't request this, contact goalpilot@goal-pilot.com immediately.\n\n"
        "Thanks for trying GoalPilot. \u2014 GoalPilot Team"
    )
    return await send_email(to=to, subject=subject, html=html, text=text)


async def send_subscription_cancelled_email(to: str, name: str | None, plan: str) -> bool:
    safe_name = (name or '').strip() or 'there'
    pretty = (plan or '').upper()
    subject = f'Your GoalPilot {pretty} plan was cancelled'
    html = f"""\
<div style=\"font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:560px;margin:0 auto;color:#0f172a\">
  <h1 style=\"color:#FF5E00;font-size:22px;margin-bottom:0\">Subscription cancelled</h1>
  <p>Hi {safe_name},</p>
  <p>Your <strong>{pretty}</strong> plan has been cancelled. You're now back on the <strong>FREE</strong> plan.</p>
  <p>Your goals and progress are safe \u2014 only the active-goal cap (1) applies again.</p>
  <p>You can re-upgrade any time from <em>Profile \u2192 Upgrade</em>.</p>
  <p>Questions? Just reply to this email.</p>
  <p style=\"color:#64748b;font-size:12px;margin-top:32px\">GoalPilot \u2022 goalpilot@goal-pilot.com</p>
</div>"""
    return await send_email(to=to, subject=subject, html=html)
