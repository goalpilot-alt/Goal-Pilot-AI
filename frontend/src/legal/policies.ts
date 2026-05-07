// Legal policies for GoalPilot — operator: GoalPilot, contact: goalpilot@goal-pilot.com, jurisdiction: Czech Republic.
// Concise SaaS-grade templates. Review with a lawyer before commercial launch.
// English is the canonical version; localized titles via i18n keys, body kept in English to ensure legal precision.

export const OPERATOR = 'GoalPilot';
export const CONTACT_EMAIL = 'goalpilot@goal-pilot.com';
export const JURISDICTION = 'Czech Republic';
export const EFFECTIVE = 'May 2026';

export const PRIVACY = `
**${OPERATOR} – Privacy Policy**
Effective: ${EFFECTIVE}

This Privacy Policy explains how ${OPERATOR} ("we", "us") collects, uses and protects your personal data when you use the GoalPilot mobile application (the "Service"). We comply with the EU General Data Protection Regulation (GDPR) and the laws of ${JURISDICTION}.

**1. Data we collect**
- Account data: name, email address, hashed password.
- Goal data: titles, deadlines, motivations, daily tasks and progress you create.
- Device data: timezone, locale, push-notification token (only if you grant permission).
- Payment data: processed exclusively by Stripe; we never store your full card details. We retain a record of the transaction (amount, plan, date) for accounting.
- Usage logs: server access logs and error reports for security and reliability.

**2. How we use your data**
- To provide the core Service (goals, tasks, AI plan, weekly review).
- To send transactional emails (account, billing) and, with your consent, push notifications and in-app reminders.
- To process payments and prevent fraud.
- To improve the product (aggregated, non-identifying analytics).

**3. AI processing**
Your goal content is sent to our AI provider (Anthropic, USA) to generate plans and reviews. The provider does not retain or train on your data per its API terms. Do not include sensitive personal information in goal text.

**4. Sharing**
We share data only with: Stripe (payments), Anthropic (AI generation), Expo / Apple / Google (push notifications), and our cloud hosting provider, all under strict data-processing agreements. We never sell your data.

**5. Retention**
We keep account data while your account is active. Payment records are retained for 10 years for tax and accounting purposes (legal obligation, ${JURISDICTION}). When you delete your account, we erase all personal data and anonymize payment records.

**6. Your rights (GDPR)**
You have the right to: access, rectify, erase, restrict, object, and port your data. Email ${CONTACT_EMAIL} to exercise any of these. You may also lodge a complaint with the Czech Office for Personal Data Protection (uoou.cz).

**7. Security**
Passwords are bcrypt-hashed. Traffic is TLS-encrypted. Access to production data is restricted to authorised personnel.

**8. Children**
The Service is not intended for users under 16. We do not knowingly collect data from children.

**9. Contact**
${OPERATOR} – ${CONTACT_EMAIL}. Governing law: ${JURISDICTION}.
`.trim();

export const TERMS = `
**${OPERATOR} – Terms of Service**
Effective: ${EFFECTIVE}

By creating an account or using the GoalPilot mobile app (the "Service") you agree to these Terms.

**1. Eligibility**
You must be at least 16 years old and able to enter a binding contract.

**2. Account**
You are responsible for maintaining the confidentiality of your credentials and for all activity under your account. Notify us immediately at ${CONTACT_EMAIL} of any unauthorised use.

**3. Subscriptions and billing**
- Free, Pro and Coach plans are described in the app. Pro and Coach are paid subscriptions billed monthly or annually via Stripe.
- Subscriptions auto-renew unless cancelled before the renewal date. You can cancel at any time from the app or by contacting ${CONTACT_EMAIL}; cancellation stops the next billing cycle.
- Prices may change with at least 30 days' notice; changes take effect on the next renewal.

**4. Refunds**
See our separate **Refund Policy**. EU consumers have a 14-day right of withdrawal under EU Directive 2011/83/EU.

**5. Acceptable use**
You agree not to: (a) reverse-engineer the Service, (b) use it for unlawful purposes, (c) attempt unauthorised access to other accounts or systems, (d) submit malicious code, or (e) use the AI features to generate harmful, illegal or infringing content.

**6. Intellectual property**
The Service, including AI-generated plan suggestions, is provided "as is" for your personal use. You retain ownership of your goal content; you grant us a limited licence to process it solely to operate the Service.

**7. AI disclaimers**
AI-generated plans are suggestions, not professional advice (medical, legal, financial, etc.). You are responsible for evaluating their suitability before acting.

**8. Termination**
You may delete your account at any time from the app. We may suspend or terminate your account for material breach of these Terms.

**9. Limitation of liability**
To the maximum extent permitted by ${JURISDICTION} law, our aggregate liability is limited to the fees you paid in the 12 months preceding the claim. We are not liable for indirect, incidental or consequential damages.

**10. Governing law**
These Terms are governed by the laws of ${JURISDICTION}. Disputes will be resolved by the courts of ${JURISDICTION}.

**11. Changes**
We may update these Terms; we will notify you in-app or by email at least 14 days before material changes take effect.

**12. Contact**
${OPERATOR} – ${CONTACT_EMAIL}.
`.trim();

export const REFUND = `
**${OPERATOR} – Refund Policy**
Effective: ${EFFECTIVE}

This Refund Policy applies to paid subscriptions to GoalPilot (Pro, Coach).

**1. Standard policy: cancel anytime**
Subscriptions are billed in advance. You may cancel at any time from the app; your subscription remains active until the end of the current paid period. Once a paid period has begun we generally do not issue prorated refunds.

**2. EU 14-day right of withdrawal**
If you are an EU consumer, you have the right to withdraw from your subscription within **14 calendar days** of the initial purchase, without giving any reason. To exercise this right, email ${CONTACT_EMAIL} from the email address associated with your account, with the subject "Refund request".
- Refunds will be issued within 14 days to the original payment method.
- By starting to use AI plan generation immediately, you consent to performance of the Service during the withdrawal period; this may, at our discretion, reduce the refundable amount proportionally.

**3. Annual subscriptions**
For annual plans cancelled outside the 14-day withdrawal window, no refund is issued for the unused portion. Your access continues until the end of the paid year.

**4. Exceptional cases**
If the Service is materially broken or unavailable for an extended period, we may issue a refund or service credit at our discretion. Contact ${CONTACT_EMAIL}.

**5. Disputes / chargebacks**
Please contact us first. Filing a chargeback without contacting us may result in account termination.

**6. Contact**
${OPERATOR} – ${CONTACT_EMAIL}. Refund requests are processed within 7 business days.
`.trim();
