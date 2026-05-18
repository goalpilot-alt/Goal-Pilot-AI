"""Public legal policy pages.

Returns HTML versions of Privacy Policy, Terms of Service, and Refund Policy
suitable to use as PUBLIC URLs for app store reviewers (Google Play, Apple).

Routes:
  GET /api/legal/privacy
  GET /api/legal/terms
  GET /api/legal/refund

These are PUBLIC — no auth required. Always returns English (canonical version).
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()

OPERATOR = 'GoalPilot'
CONTACT_EMAIL = 'goalpilot@goal-pilot.com'
JURISDICTION = 'Czech Republic'
EFFECTIVE = 'May 2026'


def _wrap(title: str, body_md: str) -> str:
    """Convert simple markdown-ish body to HTML inside a clean page."""
    html_body = []
    for line in body_md.strip().split('\n'):
        s = line.strip()
        if not s:
            html_body.append('')
            continue
        # Bold via **...** -> <strong>
        while '**' in s:
            s = s.replace('**', '<strong>', 1)
            if '**' in s:
                s = s.replace('**', '</strong>', 1)
        if s.startswith('- '):
            html_body.append(f'<li>{s[2:]}</li>')
        else:
            html_body.append(f'<p>{s}</p>')
    content = '\n'.join(html_body).replace('<p></p>', '<br/>')
    # wrap consecutive <li> in <ul>
    content = content.replace('<li>', '<ul><li>', 1) if '<li>' in content else content
    # very lightweight — for compliance pages this is enough
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{title} · {OPERATOR}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; color: #0f172a; line-height: 1.6; }}
    h1 {{ color: #FF5E00; font-size: 28px; }}
    h2 {{ font-size: 18px; margin-top: 28px; }}
    p, li {{ font-size: 15px; }}
    ul {{ padding-left: 20px; }}
    strong {{ color: #0f172a; }}
    a {{ color: #FF5E00; }}
    footer {{ color: #64748b; font-size: 12px; margin-top: 48px; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
  </style>
</head>
<body>
<h1>{title}</h1>
{content}
<footer>{OPERATOR} · <a href=\"mailto:{CONTACT_EMAIL}\">{CONTACT_EMAIL}</a> · Governed by the laws of {JURISDICTION}.</footer>
</body>
</html>"""


PRIVACY = f"""
**{OPERATOR} – Privacy Policy**
Effective: {EFFECTIVE}

This Privacy Policy explains how {OPERATOR} ("we", "us") collects, uses and protects your personal data when you use the GoalPilot mobile application (the "Service"). We comply with the EU General Data Protection Regulation (GDPR) and the laws of {JURISDICTION}.

**1. Data we collect**
- Account data: name, email address, hashed password.
- Goal data: titles, deadlines, motivations, daily tasks and progress you create.
- Device data: timezone, locale, push-notification token (only if you grant permission).
- Payment data: processed exclusively by Stripe; we never store your full card details. We retain a record of the transaction (amount, plan, date) for accounting.
- Usage logs: server access logs and error reports for security and reliability.

**2. How we use your data**
- To provide the core Service (goals, tasks, AI plan, weekly review).
- To send transactional emails (account, billing) and, with your consent, push notifications and in-app reminders.
- To improve reliability and detect abuse.

**3. AI processing**
- We send your goal text (title, deadline, motivation, level, hours/week) to Anthropic (Claude) to generate your plan. We do NOT share your name, email or payment data with Anthropic. Anthropic processes the prompt and returns a plan; it does not train on your data per their API terms.

**4. Legal basis (GDPR Art. 6)**
- Performance of contract (providing the Service).
- Consent (push notifications, marketing communications).
- Legitimate interest (security, fraud prevention).
- Legal obligation (accounting records).

**5. Sharing**
- Stripe (payment processing, USA & EU; PCI-DSS Level 1).
- Anthropic (AI plan generation, USA).
- Resend (transactional emails, USA & EU).
- Expo / Google FCM / Apple APNs (push notification delivery — only if you opt in).
- We do NOT sell your data.

**6. Your rights**
You have the right to access, rectify, port and erase your data, and to restrict or object to processing. You can:
- Export your data in-app or by contacting us.
- Delete your account in-app: Profile → Delete Account (Article 17 of GDPR). All goals, tasks, push tokens and AI plans are hard-deleted. Payment records are kept anonymized (no link to identity) for 10 years as required by Czech accounting law.
- Withdraw consent at any time (notifications toggle in Profile → Smart Reminders).
- Lodge a complaint with the Czech Data Protection Authority (uoou.cz) or your local supervisor.

**7. Data retention**
- Active account data: kept while your account is active.
- Deletion: hard-deleted on request (see §6).
- Payment records: 10 years (Czech accounting law), anonymized.
- Server logs: 30 days rolling.

**8. Security**
- Passwords are hashed with bcrypt. Network traffic is HTTPS only. Access tokens are JWT and expire. We never store full payment card data.

**9. Children**
The Service is not directed to children under 16. We do not knowingly collect data from anyone under 16.

**10. Contact**
For any privacy question, contact us at {CONTACT_EMAIL}.
"""

TERMS = f"""
**{OPERATOR} – Terms of Service**
Effective: {EFFECTIVE}

These Terms govern your use of the {OPERATOR} mobile application and related services (the "Service") provided by {OPERATOR}.

**1. Account**
You must be at least 16 years old to create an account. You are responsible for the security of your password.

**2. Subscription plans**
- Free: 1 active goal, basic features.
- Pro ($12/month or annual equivalent): up to 5 active goals, AI plan generation, calendar sync, weekly review.
- Coach ($29/month or annual equivalent): unlimited goals, daily coaching.
Plans renew automatically unless cancelled. You can cancel any time in-app (Profile → Cancel subscription) — your paid features remain until the end of the billing period.

**3. Acceptable use**
You agree not to use the Service to (a) violate any law, (b) infringe intellectual property, (c) attempt to disrupt or reverse-engineer the Service, (d) submit goals or content that is unlawful, harmful, harassing or hateful.

**4. AI-generated content**
Plans, milestones and weekly reviews are generated by an AI model and are provided "as is" for guidance. You are responsible for any actions you take based on the AI output. The Service is not a substitute for professional advice (medical, legal, financial, etc.).

**5. Intellectual property**
The Service, including its design, code, brand, and AI prompts, is owned by {OPERATOR}. You retain ownership of the goals and content you create. By using the Service, you grant us a limited license to process and store this content to provide the Service.

**6. Liability**
To the maximum extent permitted by law, {OPERATOR} is not liable for indirect, incidental or consequential damages. Our total liability is capped at the amount you paid for the Service in the 12 months preceding the claim.

**7. Termination**
We may suspend or terminate your account if you breach these Terms or use the Service in a way that endangers other users or our infrastructure. You may delete your account at any time in-app.

**8. Changes**
We may update these Terms. We'll notify you in-app or by email at least 14 days before material changes take effect. Continued use after that constitutes acceptance.

**9. Governing law**
These Terms are governed by the laws of {JURISDICTION}. EU consumer protection rights are not affected. Disputes shall be resolved by the competent courts of {JURISDICTION}, unless mandatory consumer law specifies otherwise.

**10. Contact**
Questions? Email {CONTACT_EMAIL}.
"""

REFUND = f"""
**{OPERATOR} – Refund Policy**
Effective: {EFFECTIVE}

We want you to be happy with GoalPilot. The following refund rules apply.

**1. EU 14-day right of withdrawal**
If you are a consumer resident in the European Union, you have a statutory right to withdraw from your subscription within 14 days of purchase, without giving any reason, and receive a full refund — UNLESS you have already actively used the paid features (started consuming the digital content), in which case you waive the withdrawal right.
By upgrading and using a paid feature (e.g. creating a second goal on Pro, or requesting an AI plan) you explicitly acknowledge that you start receiving the service immediately and you lose the 14-day withdrawal right (Section 1837 of the Czech Civil Code; Art. 16(m) of EU Directive 2011/83/EU).

**2. Discretionary refunds**
Outside the 14-day window, refunds are at our sole discretion. We may grant a partial or full refund for:
- Technical failures we cannot resolve within a reasonable time.
- Billing errors (charged twice, wrong plan).
- A genuine misunderstanding within the first 7 days of a paid period.

**3. How to request a refund**
Email {CONTACT_EMAIL} from your account email, including:
- Plan and amount charged.
- Date of charge (or last 4 digits of Stripe receipt id).
- Reason for the request.
We'll respond within 5 business days.

**4. Refund method**
Refunds are issued via the original payment method (Stripe) and typically reach your account within 5-10 business days.

**5. Cancellation vs. refund**
Cancelling your subscription stops future renewals — it does NOT automatically refund the current billing period. You keep access to paid features until the end of the period.

**6. Contact**
{CONTACT_EMAIL}
"""


@router.get('/legal/privacy', response_class=HTMLResponse)
async def get_privacy():
    return HTMLResponse(_wrap('Privacy Policy', PRIVACY))


@router.get('/legal/terms', response_class=HTMLResponse)
async def get_terms():
    return HTMLResponse(_wrap('Terms of Service', TERMS))


@router.get('/legal/refund', response_class=HTMLResponse)
async def get_refund():
    return HTMLResponse(_wrap('Refund Policy', REFUND))


@router.get('/legal/{kind}')
async def get_legal_404(kind: str):
    raise HTTPException(status_code=404, detail=f"Unknown legal page '{kind}'. Available: privacy, terms, refund.")
