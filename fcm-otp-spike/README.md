# FCM OTP spike

Isolated prototype to test "OTP delivered via Firebase Cloud Messaging push, instead of SMS." Does not touch the real app — `frontend/` and `backend/` still run on Cognito's `SMS_OTP` exactly as before.

## What this proves (and what it can't)

- **Cost**: FCM is free on Firebase's Spark plan, no per-message charge. If this works, your SMS carrier cost and the AWS spending-limit problem both go away for phone verification.
- **Delivery reliability — the real question**: Android handles high-priority data pushes to a backgrounded/killed app reliably. iOS does not guarantee background push delivery or timing — Apple can delay or drop silent pushes, especially under low-power mode. This is the actual risk for an OTP flow, more than the code itself. Run this on a real iOS device, not just Android, before trusting it.
- **Why not Expo Go**: a raw FCM device token (`messaging().getToken()`) isn't available in Expo Go — it needs the native Firebase SDK, so this app runs through an EAS **dev client** build, not `expo start` alone.

## One-time manual setup (you do this part — needs your own Google account)

1. Go to the [Firebase console](https://console.firebase.google.com), create a project (free Spark plan is enough).
2. Add an Android app with package name `com.searchincircle.fcmotpspike` → download `google-services.json` → place it at `fcm-otp-spike/app/google-services.json`.
3. Add an iOS app with bundle id `com.searchincircle.fcmotpspike` → download `GoogleService-Info.plist` → place it at `fcm-otp-spike/app/GoogleService-Info.plist`.
4. Project settings → Service accounts → Generate new private key → save the JSON as `fcm-otp-spike/server/firebase-service-account.json`.

Both of those downloaded files, and the service account JSON, are already covered by this repo's root `.gitignore`? Check before committing — they contain credentials and must never be pushed.

## Running it

```bash
# 1. Backend
cd fcm-otp-spike/server
cp .env.example .env
npm install
npm start   # listens on :4100

# 2. Find your machine's LAN IP (so a physical phone can reach the backend)
ipconfig getifaddr en0   # macOS, Wi-Fi

# 3. Edit fcm-otp-spike/app/App.js — set SERVER_URL to that IP, e.g. http://192.168.1.23:4100

# 4. Mobile app (needs a dev client build — this step needs an Expo/EAS account)
cd fcm-otp-spike/app
npm install
npx eas build --profile development --platform android   # or ios
# install the resulting build on your device, then:
npx expo start --dev-client
```

## Flow

1. App requests notification permission, gets an FCM token, shows it on screen.
2. Enter a phone number, tap **Register device token** — backend stores `phone -> token` in memory.
3. Tap **Send OTP** — backend generates a 6-digit code, stores it with a 5-minute expiry, sends it as an FCM **data-only** message (`android: priority high`, `apns: content-available`) to that token.
4. Foreground: the code shows directly in the app (`onMessage` handler). Backgrounded/killed: `index.js`'s `setBackgroundMessageHandler` fires and logs the payload — in a real build this is where you'd stash it (`AsyncStorage`, or a local notification) for the UI to pick up next time it's opened.
5. Tap **Verify** (or let a real build auto-submit the received code) — backend checks it against what it stored.

## What's intentionally left out (spike, not production)

- In-memory OTP/token store — a real build needs Postgres/Redis plus rate limiting (max attempts, resend cooldown) exactly like Cognito already enforces for you today.
- No auth/session issuance after verify — this only proves "did the code arrive and match," not login. Wiring it to issue your own session tokens is a separate step once you decide this direction is worth keeping.
- No TLS, no backend auth — don't point this at anything but your own test phone.

## Decision this is meant to inform

Run it on both an Android and an iOS device for a few days. If iOS silent delivery is flaky, the "silent" part of this option doesn't hold up for OTP — you'd fall back to a visible push notification (not silent) showing the code in the tray, which is still free and still better than SMS cost, just not auto-filled.
