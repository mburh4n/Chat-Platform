# PDF Chat Platform: project conventions

Full requirements: docs/Project.pdf. Read it before starting any phase.

## Stack
FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL/pgvector (pgvector/pgvector:pg16),
React (Vite, JavaScript) + React Router + Axios, Docker Compose, a separate MCP server.
LLM provider: Google Gemini (key in GEMINI_API_KEY). Verify current model names and
SDK usage from official docs before using them; do not rely on memory.

## Already built (do not rewrite, extend instead)
- core/config.py (pydantic-settings, all config from root .env), core/database.py
  (engine, SessionLocal, Base, get_db), core/security.py (pwdlib Argon2, HMAC OTPs with
  OTPPurpose, PyJWT tokens with sub/tv/type/iat/exp, DUMMY_PASSWORD_HASH),
  core/exceptions.py (AppError subclasses + handler in main.py), core/fields.py
  (Email, PersonName, NewPassword, LoginPassword, OTPCode), core/schemas.py.
- models: User (token_version), EmailOTP, PasswordResetOTP; import every model in
  app/models/__init__.py.
- emails/: send_email, templates (html.escape user input), otp_service
  (create_otp with cooldown, consume_otp with FOR UPDATE, attempts, expiry), safe_send.
- auth: signup, verify-email, resend-verification, login (timing-safe).
- frontend: api/client.js (interceptors, token storage), api/errors.js,
  api/auth.js, AuthProvider/useAuth, ProtectedRoute, PublicOnlyRoute, Layout,
  index.css classes (card, form-field, field-error, alert-*, btn, btn-link).

## Backend rules
- Pattern: router -> service -> database. Routers thin; services raise AppError
  subclasses, never HTTPException.
- Every endpoint sets response_model. Never return hashed_password or token_version.
- Use plain `def` for routes that use the DB session.
- Every schema change goes through an Alembic autogenerate migration; review it.
- Every query on user-owned data filters by the current user's id. Another user's
  document returns 404, never 403.
- Timezone-aware datetimes only: datetime.now(timezone.utc).
- "Send me a code" endpoints return identical responses whether or not the email exists.
- Secrets only in .env; update .env.example (placeholders only) for every new variable.
- Add every new package to backend/requirements.txt.

## Frontend rules
- All API calls go through functions in src/api/*.js using the shared `api` instance.
- Every form: client-side validation, field errors via getFieldErrors, summary via
  getErrorMessage, loading state that disables the submit button.
- OTPs are always sent as strings.

## Workflow
- Work in the phases of the kickoff prompt. After each phase: run the relevant tests,
  fix failures, then commit with a clear message. Never push without asking.
- When you need something only I can provide (OTP codes from email, API keys,
  decisions), stop and ask.