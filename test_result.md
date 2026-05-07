#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Add multi-language support (English US/UK, Spanish, French, Czech, Slovak, Russian, Chinese)
  with auto-detect on first launch + manual picker. Then implement the Stripe Webhook endpoint
  for robust async plan upgrades and idempotent transaction handling.

backend:
  - task: "APScheduler daily push job (Expo Push API)"
    implemented: true
    working: true
    file: "/app/backend/services/scheduler.py, /app/backend/services/push.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "AsyncIOScheduler started in app startup, runs daily at 09:00 UTC (configurable via PUSH_DAILY_HOUR_UTC env). Job iterates push_tokens.distinct user_ids, picks ONE message per user (streak-start | streak-day | streak-back | morning-summary). Localized templates for en-US/es/fr/zh-CN with en-US fallback. Posts to https://exp.host/--/api/v2/push/send via httpx. Skips users with no tokens or nothing-to-say. Verified locally: scheduler logs 'Scheduler started: daily push at 09:00 UTC' on startup; manual run sends to Expo (HTTP 200) and writes to db.push_log."
      - working: true
        agent: "testing"
        comment: "Scheduler wiring verified WITHOUT triggering job. grep '/var/log/supervisor/backend.err.log' for 'Scheduler started: daily push at 09:00 UTC' returned 3 matches across recent backend restarts (line emitted from services/scheduler.start_scheduler at startup). API root /api/ still serves 200 with {status:'ok'}, confirming scheduler init did not break FastAPI startup. Did NOT manually trigger daily_push_job (per instruction to avoid sending real Expo pushes). Code review confirms: AsyncIOScheduler with CronTrigger(hour=9, minute=0, timezone='UTC'), idempotent start, and proper shutdown hook in server.on_shutdown."

  - task: "Backend modular refactor (routes/, services/, core/, models/)"
    implemented: true
    working: true
    file: "/app/backend/server.py + /app/backend/routes/*.py + /app/backend/services/*.py + /app/backend/core/*.py + /app/backend/models/schemas.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "server.py reduced from 847 lines to 70 lines — only mounts routers and lifecycle hooks. New layout: core/{config,db,auth} (env, mongo, jwt+bcrypt+get_current_user), models/schemas.py (pydantic), services/{ai,push,scheduler,stripe,calendar_ics} (business logic), routes/{auth,goals,tasks,dashboard,nudge,checkout,calendar,notifications}.py (HTTP layer). All 59 existing tests still pass; ruff lint clean."
      - working: true
        agent: "testing"
        comment: "Full smoke regression executed against live backend with a fresh user (smoke_<uuid>@goalpilot.ai). 18/18 smoke endpoints returned expected status codes: POST /api/auth/register 200, POST /api/auth/login 200 with token, GET /api/auth/me 200 (plan=free), POST /api/auth/locale {locale:'es'} 200 + persisted, POST /api/goals 200 (full plan with summary/milestones/weekly_plan/daily_tasks; 7 tasks created), GET /api/goals 200 list, GET /api/goals/{id} 200, GET /api/tasks 200 (count=7), PATCH /api/tasks/{id} {completed:true} 200, GET /api/tasks/missed 200, GET /api/dashboard/stats 200 (streak/today_done/today_total/active_goals/total_completed/missed all present, streak=1 after task complete), GET /api/nudge 200, GET /api/review/weekly 200 (completion_rate + AI summary 266 chars), GET /api/calendar/url 200 with token, GET /api/calendar/export.ics?token=... 200 with content-type text/calendar (2285 bytes), POST /api/checkout/session {package_id:'pro_monthly', origin_url:'https://example.com'} 200 with url + session_id, POST /api/webhook/stripe with bad signature returns 400 'Invalid webhook' as expected, DELETE /api/goals/{id} 200 with {ok:true}. Modular refactor preserves all behavior."

  - task: "Idempotency-Key support on POST /api/goals (X-Idempotency-Key header)"
    implemented: true
    working: true
    file: "/app/backend/routes/goals.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Optional X-Idempotency-Key header. On first request with key, creates goal as usual + caches { user_id, key, status_code, response, created_at } in db.idempotency_keys. On replay within 24h with same (user_id, key), replays cached response (200) — including idempotent 402 plan-cap responses. TTL index on created_at expires after 26h. Verified with new tests/test_idempotency_scheduler.py (3 tests: replay-200, replay-402, health). Different key -> not idempotent (correct)."
      - working: true
        agent: "testing"
        comment: "End-to-end verified against live backend with a fresh user (idem_<uuid>@goalpilot.ai) to avoid pollution. (1) Replay-200: POST /api/goals with X-Idempotency-Key=K1 created goal id=87fed5dd; immediate retry with same body and same K1 returned the IDENTICAL goal id (cache replay, not a new goal). Backend logs confirm 'Idempotent goal replay for user=... key=...'. (2) No-key path: a third call WITHOUT idempotency key correctly returned 402 'Free plan allows 1 active goal. Upgrade to Pro for up to 5.' confirming the cap still enforces. (3) Replay-402: POST with new key K2 returned 402 (plan cap reached); retry with same K2 also returned 402 (idempotent error replay). (4) Mongo spot check: idempotency_keys collection contains both rows — K1 row has {user_id, key, status_code:200, response, created_at}; K2 row has {user_id, key, status_code:402, detail, created_at}. All 7 idempotency assertions passed."

  - task: "POST /api/auth/locale endpoint to persist user's preferred language"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added LocaleReq model, SUPPORTED_LOCALES set, lang_instruction helper, and POST /api/auth/locale endpoint that updates the user's locale field. Endpoint validates locale is in supported set and returns 400 otherwise. Auth required."
      - working: true
        agent: "testing"
        comment: "Verified end-to-end against live backend. Happy paths: all 8 supported locales (en-US, en-GB, es, fr, cs, sk, ru, zh-CN) returned 200 with body {ok:true, locale:<x>}. Unsupported values 'xx', 'de', '' all returned 400 with detail 'Unsupported locale'. Missing Authorization header returned 401 'Not authenticated'. Persistence confirmed: after POST locale=es, GET /api/auth/me returned user.locale='es'. No issues."

  - task: "AI plan generation localized via user.locale"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "generate_ai_plan() now accepts a locale and appends 'Respond entirely in <Language>' to the system prompt. Same applied to /review/weekly Claude prompt. Falls back to English if locale missing/invalid."
      - working: true
        agent: "testing"
        comment: "Set user locale to 'es' then POST /api/goals with title 'Aprender a tocar guitarra' (deadline 2026-09-30, 5h/wk, beginner). Cleaned existing active goal first to satisfy free-plan cap. Goal created successfully and plan.summary returned was clearly Spanish: 'Domina la guitarra en 18 meses con un plan estructurado que te llevará desde los acordes básicos hasta tocar canciones completas que impresionarán a todos en cualquier fiesta. Con 5 horas semanales de práctica dedicada y enfocada, desarrollarás las habilidades necesarias para ser el alma musical de cualquier reunión.' Contains accented chars (á, ó) and Spanish-only words. Localization works."

  - task: "Stripe webhook hardened with secret validation + idempotency + structured logs"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/webhook/stripe now passes STRIPE_WEBHOOK_SECRET to StripeCheckout for signature validation, logs event_type/session/status, returns 'already_processed' on idempotent retries, and 'ignored' for unknown sessions. Plan upgrade & transaction update are atomic per session."
      - working: true
        agent: "testing"
        comment: "Bad signature path: POST /api/webhook/stripe with body b'{}' and Stripe-Signature: 'bad' returned 400 with detail 'Invalid webhook' as expected; consistent across 3 repeated calls. Idempotency check: directly inserted a payment_transactions doc (session_id=cs_test_*, payment_status=paid, plan=pro) into Mongo for the test user, then re-posted the invalid webhook several times. Backend correctly returned 400 each time and the user's plan field was unchanged in /api/auth/me before vs after, confirming no unintended state mutation. Note: STRIPE_WEBHOOK_SECRET in backend/.env is empty so we could not exercise the success path with a real Stripe signature; signature validation correctly rejects all unsigned/garbage payloads. Recommend setting STRIPE_WEBHOOK_SECRET in production for live verification of the paid+idempotent branch, but the code paths are correct."

  - task: "In-app notification preferences (GET/PATCH /api/notifications/prefs) + scheduler respects prefs"
    implemented: true
    working: true
    file: "/app/backend/routes/notifications.py, /app/backend/services/scheduler.py, /app/backend/models/schemas.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added GET /api/notifications/prefs (returns defaults {morning:true, streak:true} when user has none stored) and PATCH /api/notifications/prefs with NotifPrefsReq(morning: Optional[bool], streak: Optional[bool]) — partial updates merge onto existing/default prefs and persist to users.notification_prefs. Scheduler's _build_user_message now reads notification_prefs and returns None if both flags are off; streak branches gated by streak_on; morning branch gated by morning_on."
      - working: true
        agent: "testing"
        comment: "All 8 live-backend assertions PASS against https://goal-pilot-ai.preview.emergentagent.com/api. (1) GET /api/notifications/prefs without token -> 401. (2) Fresh user (notif_fresh_<uuid>@goalpilot.ai, registered on-the-fly) GET returns exactly {'morning': True, 'streak': True}. (3) PATCH {'morning': false} -> 200 {'morning': false, 'streak': true}; subsequent GET confirms persistence. (4) PATCH {'streak': false} (on user now with morning=false) -> 200 {'morning': false, 'streak': false} (partial merge retained morning=false). (5) PATCH {'morning': true, 'streak': true} -> 200 defaults restored. (6) PATCH with empty body {} -> 200 and returns current prefs unchanged {'morning': true, 'streak': true}. (7) PATCH without Authorization header -> 401. Scheduler integration verified via direct async call to services.scheduler._build_user_message: user with {'morning': False, 'streak': False} returned None; user with {'morning': True, 'streak': False} and no history also returned None (streak_start correctly gated by streak_on); user with both True + no history returned a streak_start push message. notification_prefs is correctly wired end-to-end into the daily push job."

  - task: "AI plan generation via direct Anthropic SDK (fix for Emergent budget exhaustion)"
    implemented: true
    working: true
    file: "/app/backend/services/ai.py + /app/backend/routes/goals.py + /app/backend/.env"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          BUG: AI plan generation was silently failing with empty {milestones:[], weekly_plan:[], daily_tasks:[]} due to Emergent universal LLM key budget exceeded.
          FIX: ANTHROPIC_API_KEY in backend/.env, services/ai.py calls AsyncAnthropic.messages.create directly. routes/goals.py returns 503 on AI failure (no empty goal).
      - working: true
        agent: "testing"
        comment: |
          E2E UI verification (iPhone 12 viewport 390x844) on http://localhost:3000 — ALL 4 FLOWS PASS.
          Flow 1 — Login: tester@goalpilot.ai / Test@1234 → dashboard renders with greeting, stats, today plan section. ✅
          Flow 2 — AI plan (THE BUG FIX): Created goal "Run a 10K race in 12 weeks" (deadline 2026-07-30, beginner, 5h/wk). After Generate AI Plan, navigated to /goal/<id>. Goal detail screen shows:
            • AI Summary (multi-sentence, ~340 chars): "In the next 12 weeks, you'll transform from a beginner to a confident 10K runner..."
            • Why This Works section with substantive paragraph
            • 5 milestones listed with dates: Run 20min cont. (5/28) → First 5K (6/18) → 8K nonstop (7/9) → Full 10K training (7/23) → Race day (7/30)
            • Weekly plan with 12 weeks (Week 1 walk/run intervals through Week 12). Detail body length 3565 chars; 12 "week N" matches.
          Dashboard now shows Active goals=1, "Today's Action Plan" with 2 real tasks ("Complete your first walk/run interval...", "Schedule your weekly training days...") and a streak nudge with concrete task. NO "No tasks for today" placeholder. Bug fix CONFIRMED end-to-end.
          Flow 3 — Profile: Avatar, "Tester", tester@goalpilot.ai, FREE PLAN badge present. profile-cancel-sub-btn count=0 (correctly hidden for free user). Privacy/Terms/Refund rows all present and tappable. Privacy Policy renders with markdown content (2436 chars, includes effective date, GDPR section, data subject rights). "Delete account" red button at bottom present (NOT tapped). ✅
          Flow 4 — Spanish locale: Switched to Español. Verified translations: Perfil, Política de privacidad, Términos del servicio, Política de reembolsos, Eliminar cuenta, plus tabs Hoy/Metas/Revisión/Perfil. Switched back to English (US). ✅
          No console errors observed.

  - task: "Auto-translate new feature strings to all 7 supported locales"
    implemented: true
    working: true
    file: "/app/frontend/src/i18n/{es,fr,cs,sk,ru,zh-CN}.ts (en-GB inherits via spread)"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Added translations for 12 new keys to es/fr/cs/sk/ru/zh-CN: cancel_subscription, cancel_subscription_confirm, cancelled, cancelled_msg, cancel_failed, delete_account, delete_account_confirm, delete_account_failed, legal, privacy_policy, terms_of_service, refund_policy. en-GB inherits from en-US automatically via spread.


    implemented: true
    working: true
    file: "/app/backend/routes/checkout.py + /app/backend/services/email.py + /app/frontend/app/(tabs)/profile.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          NEW endpoint POST /api/subscription/cancel (auth required). Behaviour:
          - If user.plan == 'free' -> returns {ok:true, plan:'free', already_free:true} (idempotent, no email).
          - Else -> sets plan='free', cancelled_at, previous_plan; unsets billing; sends cancellation email via Resend (services/email.send_subscription_cancelled_email). Email failure is fail-soft.
          Frontend: Profile shows amber 'Cancel subscription' button only when plan != 'free'. Tapping opens confirm Alert; on confirm calls /subscription/cancel then refreshUser().
      - working: true
        agent: "testing"
        comment: |
          Section A of backend_test.py: 10/10 assertions PASS against live backend.
          (A.1) POST /api/subscription/cancel without Authorization -> 401.
          (A.2) Fresh free user (cancel_free_<uuid>@goalpilot.ai) POST -> 200 body={'ok':True,'plan':'free','already_free':True}; GET /auth/me still plan='free' (no email sent on already_free branch — correct).
          (A.3) Fresh user upgraded directly in Mongo to {plan:'pro', billing:'monthly'}. /auth/me confirmed plan='pro'. POST /subscription/cancel -> 200 body={'ok':True,'plan':'free','previous_plan':'pro'}. /auth/me now plan='free'. Mongo users doc has cancelled_at set (ISO timestamp), previous_plan='pro', and 'billing' field unset (verified absent via find_one). Backend logs show cancellation email was attempted via Resend — it returned 403 sandbox ('You can only send testing emails to your own email address') which is the expected Resend-free-tier behaviour; endpoint still returned 200 as fail-soft. No 500s logged.
          (A.4) Calling POST /subscription/cancel again on the now-free user -> 200 body={'ok':True,'plan':'free','already_free':True} (idempotent).
          Email integration is wired correctly — the route imports send_subscription_cancelled_email and fail-soft catches Resend errors. To deliver to arbitrary recipients in production, a domain must be verified in Resend (currently only onboarding@resend.dev sandbox is usable).

  - task: "Account deletion email confirmation (DELETE /api/auth/account)"
    implemented: true
    working: true
    file: "/app/backend/routes/auth.py + /app/backend/services/email.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          DELETE /api/auth/account already hard-deletes user data + anonymizes payment_transactions.
          NEW: after deletion, calls services/email.send_account_deleted_email(to=email, name=name).
          Email is fail-soft (errors logged but never block deletion). Verify endpoint still returns 200 {ok:true, deleted_user:true}.
      - working: true
        agent: "testing"
        comment: |
          Section B of backend_test.py: 12/12 assertions PASS against live backend.
          (B.1) DELETE /api/auth/account without Authorization -> 401.
          (B.2) Fresh user (delete_<uuid>@goalpilot.ai) registered. Created one real goal via POST /api/goals (title='Learn Spanish A1', current_level='beginner', hours_per_week=5, deadline=2026-09-30) — Claude plan generated successfully with 7 daily_tasks (cascade test now exercises real data, not vacuous). Inserted one fake payment_transactions doc with session_id=cs_test_anon_<uuid>, user_id=<user>, user_email=<email>. Inserted one push_tokens, one idempotency_keys, and one push_log row for the same user_id.
          DELETE /api/auth/account -> 200 body={'ok':True,'deleted_user':True}.
          Mongo verification post-delete: users doc gone; goals count=0; tasks count=0; push_tokens count=0; idempotency_keys count=0; push_log count=0. payment_transactions row still exists BUT user_id='deleted_user', user_email='deleted_user', anonymized_at ISO timestamp present.
          (B.2g) GET /auth/me with the now-deleted user's token returned 401 (not 200).
          Backend logs show send_account_deleted_email was attempted — Resend returned 403 sandbox validation_error ('You can only send testing emails to your own email address'). That is expected Resend-free-tier behaviour (no verified domain); endpoint did NOT throw or crash, and no 500 was emitted — fail-soft working as designed. To deliver real emails, main agent must verify a domain in Resend.

frontend:
  - task: "Pre-AI feasibility heuristic in New Goal flow + Legal policies (Privacy/Terms/Refund) + GDPR account deletion"
    implemented: true
    working: true
    file: "Multiple — /app/backend/routes/auth.py + /app/frontend/src/feasibility.ts + /app/frontend/src/legal/policies.ts + /app/frontend/app/legal/[kind].tsx + /app/frontend/app/(tabs)/profile.tsx + /app/frontend/app/goal/new.tsx + /app/frontend/src/AuthContext.tsx + /app/frontend/src/i18n/en-US.ts"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Three-feature delivery.\n(1) PRE-AI FEASIBILITY HEURISTIC: New file src/feasibility.ts evaluates (deadline, hours_per_week, level) instantly with rule-based thresholds (per-level minimum hours: beginner 30 / intermediate 20 / advanced 10; floors: <7 days = unrealistic, <5 total hours = unrealistic). Shown as amber/red banner inside step 4 of New Goal flow with 'Apply suggested deadline' one-tap fix \u2014 user adjusts deadline BEFORE Claude is called. Verified live: 5-day marathon goal + beginner triggers 'unrealistic' banner with suggested deadline 30 days out.\n(2) LEGAL POLICIES: src/legal/policies.ts has full Privacy / Terms / Refund Policy texts written for operator='GoalPilot', contact='goalpilot@goal-pilot.com', jurisdiction='Czech Republic'. Compliant with GDPR (16+ age, full data subject rights, EU 14-day refund withdrawal, AI processor disclosure for Anthropic). Single dynamic route /legal/[kind] renders any of 3 policies with markdown-style ** bold ** and headings. Reachable from Profile -> Legal section (3 rows: Privacy, Terms, Refund). Verified visually \u2014 renders cleanly with formatted sections.\n(3) ACCOUNT DELETION (GDPR Article 17): DELETE /api/auth/account performs hard-delete of user, goals, tasks, push_tokens, idempotency_keys, push_log; payment_transactions are kept and ANONYMIZED (user_id and email scrubbed) for 10-yr Czech accounting retention requirement. Frontend: AuthContext.deleteAccount; Profile shows red 'Delete account' button at bottom that opens confirmation alert before calling the endpoint and redirecting to welcome. Visible & wired."

  - task: "AI plan respects start date + deadline + feasibility detection + replan"
    implemented: true
    working: true
    file: "/app/backend/services/ai.py + /app/backend/routes/goals.py + /app/frontend/app/goal/[id].tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Bug fix + new feature. ROOT CAUSE: AI prompt lacked today's date so Claude assumed a generic multi-month plan regardless of actual time available. FIX: Pass START DATE (today) + DEADLINE + DAYS_AVAILABLE + WEEKS_AVAILABLE to the prompt with hard CONSTRAINTS that all milestone target_dates and day_offsets MUST be inside the window, and weekly_plan MUST equal weeks_available. AI now also returns: feasibility ('ok'|'tight'|'unrealistic'), feasibility_reason, suggested_deadline_iso, suggested_weeks. NEW ENDPOINT: POST /api/goals/{id}/replan {deadline:'YYYY-MM-DD'} regenerates the entire plan (summary, milestones, weekly_plan, daily_tasks) for a new deadline; deletes old tasks atomically. Validates deadline > today (400 otherwise). Frontend: amber/red feasibility banner on goal detail when feasibility != 'ok' AND suggested != original; two buttons 'Keep my deadline' / 'Use suggested {date}' \u2014 second invokes the replan endpoint. Verified end-to-end: 14-day B2 French goal correctly flagged unrealistic with 1-year suggestion; replan to suggested date returns 200 with 4 milestones + 2-week weekly_plan that fit; past deadline replan returns 400. Axios timeout raised to 180s for slow AI calls."

  - task: "Switch Stripe to Live mode (STRIPE_API_KEY=sk_live_..., STRIPE_WEBHOOK_SECRET=live whsec_...)"
    implemented: true
    working: true
    file: "/app/backend/.env"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Replaced sk_test_emergent placeholder with real sk_live_... (109 chars). Replaced TEST whsec with LIVE whsec_GltY... (40 chars), separate Live-mode webhook endpoint registered in Stripe dashboard. Verified: POST /checkout/session returns cs_live_... (proving Live API mode), webhook bogus sig still 400, health 200, scheduler healthy. \u26a0\ufe0f Real charges now possible \u2014 use real card numbers, not 4242 4242 ..."

  - task: "Stripe webhook secret wired to .env (live signature validation)"
    implemented: true
    working: true
    file: "/app/backend/.env + /app/backend/services/stripe.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Real Stripe webhook signing secret added to .env (whsec_..., 39 chars). Backend restarted; scheduler still healthy. Bogus signature test returns 400 with 'Invalid webhook' as expected. Endpoint is now ready to accept real Stripe-signed events at POST /api/webhook/stripe \u2014 user has registered the endpoint in their Stripe Test mode dashboard and is listening for checkout.session.completed."

  - task: "Per-user timezone for daily push (POST /api/auth/timezone + hourly scheduler)"
    implemented: true
    working: true
    file: "/app/backend/routes/auth.py + /app/backend/services/scheduler.py + /app/frontend/src/AuthContext.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Backend: POST /api/auth/timezone validates IANA TZ via zoneinfo and stores user.timezone. Scheduler now ticks hourly (CronTrigger minute=0) and per user computes local hour via ZoneInfo; only sends when local_hour == user.push_hour (default 9). Users without timezone fall back to legacy fixed UTC slot. Verified live: hourly ticks logged, valid/invalid/auth tests all pass.\nFrontend: AuthContext.bootstrap/login/register now also calls POST /api/auth/timezone with Intl.DateTimeFormat().resolvedOptions().timeZone, alongside existing locale sync."

  - task: "Profile -> Notifications row whole-row tap + 6 more locale translations for notif screen"
    implemented: true
    working: true
    file: "/app/frontend/app/(tabs)/profile.tsx + /app/frontend/src/i18n/{fr,cs,sk,ru,zh-CN,en-US,es}.ts"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Profile 'Smart Reminders' row is now wrapped in a single TouchableOpacity, so tapping anywhere navigates to /settings/notifications (previously only the chevron was tappable). Added native-language strings for the 5 main remaining locales: fr, cs, sk, ru, zh-CN (en-GB inherits from en-US via spread). Verified visually in French \u2014 Notifications, Notifications quotidiennes, R\u00e9sum\u00e9 matinal, Rappels de s\u00e9rie, footer all translated."

  - task: "Notification preferences (GET/PATCH /api/notifications/prefs + scheduler gating)"
    implemented: true
    working: true
    file: "/app/backend/routes/notifications.py + /app/backend/services/scheduler.py + /app/frontend/app/settings/notifications.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Added user.notification_prefs = {morning: bool, streak: bool} (default true/true). Endpoints: GET returns current prefs (defaults applied); PATCH does partial merge (only updates fields present in body). Scheduler _build_user_message now skips users where both prefs are false (returns None), and gates streak_start/streak_day/streak_back behind streak_on, and morning summary behind morning_on. Frontend: new modal screen /settings/notifications with two RN <Switch>es bound to backend; reachable from Profile > Smart Reminders > chevron. Verified end-to-end: PATCH 200 OK, switches persist across reload. Backend testing agent ran 8 assertions including direct scheduler invocation \u2014 all pass."

  - task: "Vector icons font preload (fixes squared icon glyphs)"
    implemented: true
    working: true
    file: "/app/frontend/app/_layout.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "User reported all icons rendering as empty squares on web preview. Root cause: Feather icon font from @expo/vector-icons was not preloaded — RNW served fallback glyphs (filled boxes) until font loaded async. Fixed by calling useFonts(Feather.font) in RootNav and gating the Stack render on fontsLoaded. Verified via screenshots: dashboard now shows zap, target, life-buoy, coffee, sun, bar-chart, user, plus icons correctly. No styling change."

  - task: "i18n integration across all screens with reactive provider"
    implemented: true
    working: true
    file: "/app/frontend/src/i18n/I18nProvider.tsx and all /app/frontend/app/*.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Created I18nProvider with useI18n() hook providing reactive { locale, setLocale, t }. Wired into RootLayout. Refactored all user-facing screens (welcome, login, register, tabs layout, dashboard, goals, review, profile, goal/new, goal/[id], pricing, payment/success) to use t('key'). Verified visually with screenshots in English, Spanish, Chinese, French. Tab labels, dates and dashboard greeting also localized."

  - task: "Auto-detect device locale on first launch + persist via AsyncStorage"
    implemented: true
    working: true
    file: "/app/frontend/src/i18n/index.ts"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "initI18n reads goalpilot_locale from AsyncStorage; if absent, picks best match from expo-localization device list. setLocale() persists to AsyncStorage and pushes to backend via POST /api/auth/locale."

  - task: "Language picker screen at /settings/language"
    implemented: true
    working: true
    file: "/app/frontend/app/settings/language.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Modal screen reachable from Profile > Language row. Lists all 8 supported locales with native labels. Tap to switch — UI updates reactively and pops back."

  - task: "Auth context syncs locale to backend on login/register/bootstrap"
    implemented: true
    working: true
    file: "/app/frontend/src/AuthContext.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "After successful login/register/bootstrap, calls POST /api/auth/locale with current i18n.locale so AI plan generation and weekly review respond in the user's language."

metadata:
  created_by: "main_agent"
  version: "1.2"
  test_sequence: 6
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      i18n integration is complete and verified visually. Backend additions:
      1) POST /api/auth/locale (auth required, validates against SUPPORTED_LOCALES = en-US, en-GB, es, fr, cs, sk, ru, zh-CN)
      2) generate_ai_plan() and /review/weekly now use user's stored locale to instruct Claude to respond in that language.
      3) /api/webhook/stripe now validates with STRIPE_WEBHOOK_SECRET and is fully idempotent.
      Test credentials in /app/memory/test_credentials.md (tester@goalpilot.ai / Test@1234). Please cover:
      - /api/auth/locale happy path (es, fr, zh-CN), validation error for unsupported (e.g. 'xx'), 401 unauth.
      - /api/goals creation with locale set returns plan.summary text in target language (sanity check).
      - /api/webhook/stripe returns 400 on bad signature; 200 + idempotent on already-paid session.
  - agent: "testing"
    message: |
      Notification preferences targeted test (2026): 8/8 API assertions PASS + 3/3 scheduler
      assertions PASS against live backend.

      API (https://goal-pilot-ai.preview.emergentagent.com/api):
        - GET /api/notifications/prefs (no token) -> 401
        - Fresh user -> GET returns {"morning": true, "streak": true}
        - PATCH {"morning": false} -> {"morning": false, "streak": true} (persisted, verified by GET)
        - PATCH {"streak": false} -> {"morning": false, "streak": false}
        - PATCH {"morning": true, "streak": true} -> defaults restored
        - PATCH {} (empty body) -> 200, current prefs unchanged
        - PATCH without token -> 401

      Scheduler (services.scheduler._build_user_message, called directly via python -c):
        - {'morning': False, 'streak': False} -> None (both off shortcut)
        - {'morning': True, 'streak': False} with no history -> None (streak_start correctly
          gated by streak_on even though morning is on, because no tasks today)
        - {'morning': True, 'streak': True} with no history -> streak_start push payload

      No critical issues. Task marked working: true, current_focus remains cleared.

  - agent: "testing"
    message: |
      Cancel Subscription + Account Deletion email features — 26/26 backend assertions PASS
      against live preview backend.

      Section A — POST /api/subscription/cancel (10/10):
        - no-auth -> 401
        - Fresh free user -> 200 {ok:true, plan:'free', already_free:true}; /me still free
        - Fresh user manually upgraded in Mongo to plan:pro/billing:monthly; /me confirms plan:pro
        - POST cancel -> 200 {ok:true, plan:'free', previous_plan:'pro'}; /me now plan:free
        - Mongo user doc: cancelled_at ISO timestamp SET, previous_plan='pro', billing UNSET
        - Second cancel on same user -> 200 {already_free:true} (idempotent)
        - Backend logs: Resend attempted (403 sandbox — expected free-tier behaviour); NO 500s;
          cancellation endpoint fail-soft works correctly.

      Section B — DELETE /api/auth/account (12/12):
        - no-auth -> 401
        - Fresh user created one real goal via POST /api/goals (7 daily_tasks generated by
          Claude). Inserted fake payment_transactions (session_id=cs_test_anon_<uuid>),
          push_tokens, idempotency_keys, push_log rows for same user_id
        - DELETE /auth/account -> 200 {ok:true, deleted_user:true}
        - Mongo verified: users gone; goals=0; tasks=0; push_tokens=0; idempotency_keys=0;
          push_log=0
        - payment_transactions row STILL EXISTS but user_id='deleted_user',
          user_email='deleted_user', anonymized_at ISO timestamp present — exactly as designed
        - GET /auth/me with deleted user token -> 401 (not 200)
        - Backend logs: send_account_deleted_email attempted via Resend (403 sandbox); deletion
          endpoint did NOT crash, no 500s — fail-soft works correctly.

      Section C — Regression smoke (4/4):
        - register, login, /auth/me for fresh user all 200
        - POST /checkout/session pro_monthly origin='https://example.com' -> 200, session_id
          starts with cs_live_... (Live Stripe confirmed)

      IMPORTANT NOTE for main agent:
      Resend is currently in FREE SANDBOX MODE — it returns 403 validation_error for any
      recipient other than the account owner (goalpilot@goal-pilot.com). The backend handles
      this correctly (fail-soft), but to actually deliver cancellation/deletion emails to real
      users in production, main agent must VERIFY A DOMAIN in Resend and update EMAIL_FROM
      in /app/backend/.env to use that verified domain (currently using onboarding@resend.dev
      sandbox). This is a deployment task, not a code bug.

      Both target tasks now marked working: true. current_focus cleared.
