# GoalPilot AI — Google Play Store Launch Checklist

> Use this file as your single source of truth while shipping GoalPilot to Play Store.

---

## ✅ Already done (in this Emergent workspace)

- [x] **app.json** finalized for Android production
   - `expo.name`: `GoalPilot`
   - `expo.android.package`: `com.goalpilot.ai`
   - `expo.android.versionCode`: `1`
   - `expo.version`: `1.0.0`
   - Permissions: INTERNET, ACCESS_NETWORK_STATE, RECEIVE_BOOT_COMPLETED, VIBRATE, POST_NOTIFICATIONS, WAKE_LOCK
   - iOS bundle id & infoPlist also set for future iOS submission
- [x] **eas.json** created with `production` profile (AAB output)
- [x] **Public legal pages** at `/api/legal/{privacy,terms,refund}` (HTML, GDPR + Czech jurisdiction)
- [x] **Reviewer demo account** `tester@goalpilot.ai` / `Test@1234` upgraded to Pro
- [x] **AI generation** working via direct Anthropic SDK (Emergent budget no longer blocks)
- [x] Cancel-subscription + Account-deletion flows verified in backend testing
- [x] i18n for 8 locales with translations for new feature strings
- [x] Stripe LIVE mode keys configured + webhook secret installed

---

## 🟡 You do — preparation (outside Emergent, do in parallel)

- [ ] **Apple — skip for now** (going Android-first)
- [ ] **Google Play Console** — register at https://play.google.com/console → pay **$25** one-time → wait 24-48 h for approval. **Owner email**: use your real Google account.
- [ ] **expo.dev** — free account at https://expo.dev → sign in
- [ ] **Backend deployment** — click **Deploy** at the top of this Emergent chat → wait 10-15 min → **paste the new production URL back here** so I can:
   - Update `EXPO_PUBLIC_BACKEND_URL` for the build
   - Update the Stripe webhook URL in your Stripe dashboard
- [ ] **(Optional) Resend domain** — verify your domain (e.g. `goal-pilot.com`) at https://resend.com/domains so cancellation/deletion emails actually deliver
- [ ] **Local laptop setup**:
   ```bash
   # Install Node 20+ (https://nodejs.org/) then:
   npm install -g eas-cli
   eas login
   ```

---

## 📦 Store listing assets you need to prepare

| Asset | Spec | Status |
|---|---|---|
| App icon | 512×512 PNG, no transparency | ⚠️ Existing icon is 512×513 — EAS handles, but Play Store store-listing icon may need exact 512×512. I can crop if you want. |
| Feature graphic | 1024×500 PNG/JPG | ❌ Create — usually has app name + tagline + brand color (#FF5E00) |
| Phone screenshots | 2-8, 1080×1920 minimum | ❌ Take from your real Android phone or Expo Go in landscape mode |
| 7" tablet screenshots | Optional but recommended | ❌ Skip if no tablet device |
| Short description | Max 80 chars | See suggested copy below |
| Full description | Max 4000 chars | See suggested copy below |
| Privacy Policy URL | Public HTTPS URL | ✅ Will be `https://<your-prod-domain>/api/legal/privacy` after deploy |
| Content Rating | IARC questionnaire | Fill in Play Console (5 min) |
| Data Safety form | Disclose all collected data | Pre-filled below |

### Suggested short description (80 chars max)
> Turn any goal into daily wins. AI-built plans, streaks & coaching.

### Suggested full description (under 4000 chars)
> **GoalPilot AI — Your AI accountability coach.**
>
> Turn ambition into action. Tell GoalPilot what you want to achieve, by when, and how much time you can spend — and our AI coach (powered by Anthropic Claude) instantly builds a personalised plan: milestones, weekly themes, and daily tasks calibrated to your level.
>
> 🎯 **Smart goal breakdown** — Any goal, any deadline. Get 5+ milestones, a week-by-week roadmap, and 5-7 daily tasks ready to tap-and-complete.
>
> 🔥 **Streak tracking** — Compound small wins into momentum. We celebrate your streaks and gently nudge you back when life happens.
>
> 📅 **Calendar sync** — One-tap subscribe to your tasks in Apple Calendar, Google Calendar, or Outlook. Your plan, in the tools you already use.
>
> 🧠 **Weekly AI review** — Every Sunday, your coach reviews your week, celebrates the wins, and proposes one specific focus for next week.
>
> 🌍 **8 languages** — English, Spanish, French, Czech, Slovak, Russian, Simplified Chinese.
>
> 💎 **Plans**
> • Free — 1 active goal
> • Pro ($12/mo) — up to 5 goals + AI breakdown + calendar sync + weekly review
> • Coach ($29/mo) — unlimited goals + daily AI coaching
>
> Cancel anytime in Profile → Cancel subscription. EU customers benefit from the 14-day withdrawal right (unless you've already used the paid features). Full Privacy Policy & GDPR-compliant data deletion built in.
>
> Made by GoalPilot, Czech Republic.

### Data Safety form — what to declare
- **Personal info**: Name, Email address
- **App activity**: App interactions (goals, tasks, completions)
- **Device or other IDs**: Push notification token
- **Financial info**: Purchase history (Stripe handles cards)
- **Shared with third parties**: Stripe (payments), Anthropic (AI plan generation), Resend (transactional email), Expo/FCM (push)
- **Encrypted in transit**: YES (HTTPS only)
- **User can request data deletion**: YES (Profile → Delete Account)
- **Data deletion handling**: Hard-delete user/goals/tasks; payment records kept anonymized for 10y (Czech tax law)

### Content Rating
- App targets adults & teens (16+). Will likely score **PEGI 3 / ESRB Everyone** — no violence, no sensitive content.
- AI-generated text → declare "User-generated content" + "AI features" → low moderation risk since users only input their own goals.

---

## 🚀 Build & submit (run on your laptop)

```bash
# 1. Pull this repo to your laptop (Emergent → Push to GitHub → git clone)
cd path/to/goalpilot/frontend

# 2. Make sure .env has the PRODUCTION backend URL
echo "EXPO_PUBLIC_BACKEND_URL=https://<your-prod-domain>" >> .env

# 3. Install deps
yarn install

# 4. Initialize EAS (creates a project on expo.dev)
eas init

# 5. Build production AAB (~20-30 min in EAS cloud — runs on any OS)
eas build -p android --profile production

# 6. Once build finishes, download the .aab OR submit directly
eas submit -p android --latest
#    On first submission you'll be prompted to upload the Google Service Account
#    JSON key — create one at:
#    Play Console → Setup → API access → Service accounts → Create new
#    Grant role: "Release manager"
```

---

## 📋 Inside Google Play Console

1. **Create app** → fill name, default language (English-US), category (Productivity), free
2. **App access** → "All functionality is available without restrictions" only if you grant Pro to reviewer; otherwise paste tester credentials
3. **Ads** → No ads
4. **Content rating** → take IARC questionnaire (5 min)
5. **Target audience** → 16+ (or 13+; not under 13)
6. **News app?** → No
7. **COVID-19 / Government / Financial features** → none
8. **Data safety** → fill per template above
9. **Store listing** → upload all assets above; **Privacy Policy URL** = `https://<your-prod-domain>/api/legal/privacy`
10. **Pricing & distribution** → free; choose countries
11. **App releases** → Production → Create new release → upload the .aab from EAS
12. **Send for review** → Google reviews in 1-7 days (usually 2-3)

---

## ⏱ Realistic timeline

| Day | Action |
|---|---|
| **D0** | You click Deploy in Emergent; you register Play Console + expo.dev |
| **D0** | (You) Send me the new backend URL → I update Stripe webhook + .env |
| **D1** | (Wait for Google Play Console activation 24-48h) |
| **D2** | You run `eas build` (~30 min) and prepare assets |
| **D2** | Upload AAB + fill all forms in Play Console |
| **D2** | Submit for review |
| **D3-7** | Google reviews → app live 🎉 |

---

## 🆘 If something breaks

- **Build fails in EAS** → paste the error log here, I'll debug
- **Google rejects** → most common reasons:
   1. Privacy policy URL broken (we have it covered above ✅)
   2. Crash on launch → I'll add a crash-on-launch safety net before build if needed
   3. Permissions mismatch → I've already declared exactly what we use
   4. Missing demo credentials → we have tester@goalpilot.ai pre-Pro ✅
   5. AAB signed incorrectly → EAS handles automatically ✅

---

## 📞 Contact
GoalPilot · goalpilot@goal-pilot.com · Czech Republic
