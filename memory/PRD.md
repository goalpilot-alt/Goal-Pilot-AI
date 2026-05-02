# GoalPilot AI — Product Requirements Document

## Overview
GoalPilot AI is a mobile (React Native + Expo) app that turns any user goal into an AI-generated, structured plan with milestones, weekly breakdowns, and daily tasks. It uses Claude Sonnet 4.5 (via the Emergent Universal LLM key) for goal breakdown and weekly AI reviews.

**Positioning:** "Your AI accountability partner for turning goals into daily action."

## Tech Stack
- **Frontend**: Expo SDK 54 + expo-router, react-native-svg, expo-secure-store, @expo/vector-icons, expo-linear-gradient
- **Backend**: FastAPI + Motor (Async Mongo) + PyJWT + bcrypt + emergentintegrations
- **AI**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) via `EMERGENT_LLM_KEY`
- **DB**: MongoDB (`goalpilot_db`) — collections: `users`, `goals`, `tasks`

## Auth (JWT)
- `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- Bearer token (7-day lifespan), stored via `expo-secure-store` (or `localStorage` on web fallback)
- Passwords hashed with bcrypt

## Core Features Shipped (MVP)
1. **Welcome / Onboarding** — hero gradient + CTAs
2. **Register + Login** — keyboard-safe forms, inline errors
3. **Daily Dashboard** — greeting, circular progress ring, streak counter, active goals, missed tasks callout, today's checklist, tap-to-toggle completion
4. **Goals list** — status badges, milestone count, tap to open
5. **Goal creation** — 4-step form (title → deadline → motivation → level + hours/week) → AI plan generation
6. **Goal Detail** — AI summary, "why it works", milestones timeline, weekly plan accordion
7. **Weekly AI Review** — completed/missed/rate stats + AI coach summary + "next week's focus"
8. **Profile** — avatar, plan badge, smart-reminder toggle, upgrade CTA, logout
9. **Pricing** — Free/Pro/Coach plans with mocked upgrade flow

## Subscription Plans (backend-enforced)
- **Free** — 1 active goal
- **Pro ($12/mo)** — 5 goals (TODO: enforce), smart reminders, weekly review
- **Coach ($29/mo)** — unlimited

## Monetization — MOCKED
`POST /api/subscription/upgrade?plan=pro|coach` only sets `user.plan`. Real Stripe checkout is **NOT** wired — activating it requires Stripe publishable + secret keys and adding Checkout Session flow.

## Deferred / Not in MVP
- Real Stripe payments (mocked)
- Push notifications (in-app reminders UI only — no `expo-notifications` wiring)
- Calendar integration, social, teams, marketplace, gamification

## Key Files
- Backend: `/app/backend/server.py`
- Frontend entry: `/app/frontend/app/index.tsx`, `/app/frontend/app/_layout.tsx`
- Shared: `/app/frontend/src/api.ts`, `/app/frontend/src/AuthContext.tsx`, `/app/frontend/src/theme.ts`, `/app/frontend/src/ProgressRing.tsx`
- Test creds: `/app/memory/test_credentials.md`
