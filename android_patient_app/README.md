# CogniCompanion — Android Patient App

Production-oriented Android patient client for CogniCompanion, built with Kotlin, Jetpack Compose, Hilt, Retrofit, Moshi, Room and WorkManager. The app is designed to degrade gracefully under low connectivity while keeping patient data local and minimizing sensitive logging.

> **Important:** this is production-hardened application code, not a claim of clinical certification or Play Store readiness. Before a real patient release, complete clinical validation, backend security review, privacy/legal review, accessibility testing, signing/key management, monitoring and staged rollout.

## Architecture

```text
Compose UI
   ↓
ViewModel / StateFlow
   ↓
Repository
   ├── Retrofit → FastAPI backend
   ├── Room → cached dashboard/timeline
   └── Outbox → WorkManager retry

Session
   └── Android Keystore-backed encrypted preferences
```

## Reliability implemented
- Dashboard and today's timeline are cached locally and shown when the network is unavailable.
- Medication completion is queued locally if the request cannot reach the backend, then retried by WorkManager when connectivity returns.
- Network retries are limited to idempotent GET/HEAD requests so POST operations are not duplicated by the HTTP interceptor.
- Timeouts are bounded and user-facing errors are safe/generic.
- A periodic outbox worker provides a second sync opportunity every 15 minutes.

## Security implemented
- Release builds prohibit cleartext traffic; HTTP is enabled only in the debug manifest for local development.
- Authorization headers are redacted from HTTP logs. Release logging is disabled.
- Access/refresh tokens are stored using Android Keystore-backed `EncryptedSharedPreferences`, not plain DataStore.
- Android backup/device-transfer excludes app files, databases, preferences and DataStore.
- Release base URL is configured through the Gradle property `COGNI_API_BASE_URL` and should be HTTPS.

Build a release with:

```powershell
./gradlew assembleRelease -PCOGNI_API_BASE_URL=https://YOUR-DOMAIN/api/v1/
```

Do not put real production credentials or signing keys in source control.

## Local development
1. Open the project in Android Studio.
2. Install Android SDK 35.
3. Android Studio normally creates `local.properties` automatically. A template is provided as `local.properties.example`.
4. Run the backend on port 8000.
5. Debug uses `http://10.0.2.2:8000/api/v1/` for the Android emulator.
6. For a physical device, use `adb reverse tcp:8000 tcp:8000` or a LAN URL.

## Patient safety / accessibility
- Material 3 controls provide large touch targets by default.
- System font scaling is respected; avoid hardcoded text sizes when extending the UI.
- Keep patient-facing copy short and unambiguous.
- Never infer that a missing record means an action did not happen.
- Medication schedules remain backend-controlled; the patient app only records completion.
- Cognitive scores are assistive indicators and must not be presented as a diagnosis.

## Remaining release gates
Before publishing to real users, still complete:
- automated unit/repository/ViewModel tests and Compose UI tests
- backend TLS, authorization, rate limiting, audit logging and production database backups
- token refresh/session-expiry behavior if supported by the backend contract
- real-device microphone/STT/TTS testing, including interruption and poor-network cases
- TalkBack, large-font, contrast and elderly usability testing
- privacy consent, retention/deletion policy and regional regulatory review
- Play App Signing, internal/closed testing, crash reporting, analytics/monitoring and staged rollout

The current codebase is therefore **production-oriented and substantially hardened**, but it should still be treated as a pre-release build until those external release gates are completed.


## Current patient-app implementation

Implemented in this Android build:
- Home dashboard + cached timeline
- Dedicated Today / Daily Plan screen
- Games catalog + generated-game launcher + session recording
- Voice assistant using Android speech recognition and device TTS, with backend `voice/converse` integration
- Profile with patient details, emergency-contact dialer and logout
- Four-tab navigation: Home, Games, Memories, Profile
- Global voice-assistant action
- Encrypted session tokens and reactive login state
- Configurable API base URL from Server settings; include `/api/v1/`
- 401 session refresh/retry support when the backend exposes `POST /auth/refresh`

### API configuration
For a release build pass `-PCOGNI_API_BASE_URL=https://your-server.example/api/v1/`. Do not ship the example URL.
For a physical Android device in debug mode, use the computer's LAN IP instead of `10.0.2.2`, and keep HTTP only for local development.

### Android SDK
Copy `local.properties.example` to `local.properties` and set `sdk.dir` to the Android SDK installed on your Windows machine. `local.properties` should remain uncommitted.

### Voice/game contract note
The app intentionally keeps game and voice response parsing tolerant because the backend response schemas have evolved. Before a production release, run integration tests against the current FastAPI server and verify the exact `voice/converse`, `games`, `games/{type}/generate`, and `games/sessions` contracts.
