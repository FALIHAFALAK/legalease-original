# LegalEase

LegalEase is a full-stack legal document drafting and general legal-information application. It provides structured document templates, AI-assisted first drafts, rich editing, version history, PDF/DOCX export, an assistant, document review, and administration.

The application produces drafts and general information only. It is not a law firm, does not provide legal advice, and does not determine whether a document is valid, enforceable, safe, or compliant.

## Stack

- **Frontend:** Next.js App Router, TypeScript, React, Tailwind CSS, TipTap
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic
- **AI:** deterministic mock provider for development and the official `google-genai` package for Gemini
- **Storage:** SQLite by default; SQLAlchemy is configured for PostgreSQL-compatible deployments
- **Exports:** ReportLab PDF and `python-docx` DOCX
- **Tests:** pytest and TestClient

## Prerequisites

- Node.js and npm
- Python 3.11 or newer
- A Gemini API key only when using the Gemini provider

## Local setup on Windows

Open PowerShell from the project root.

### 1. Configure the environment

```powershell
Copy-Item .env.example .env
```

The default configuration uses `AI_PROVIDER=mock`, SQLite, and a local frontend origin. The mock provider is deterministic and does not require credentials; it is not used to pretend to answer legal questions. The assistant requires the Gemini provider and a valid key.

To use Gemini, edit `.env`:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Restart the backend after changing environment variables. A Gemini key is never returned by the API. If the assistant is left in mock mode, it returns a visible `ai_not_configured` error rather than a generic legal answer.

Gemini calls retry transient upstream failures (HTTP 429/5xx and "high demand"/"unavailable" responses) with exponential backoff, up to `GEMINI_MAX_ATTEMPTS` times with a `GEMINI_RETRY_BASE_SECONDS` base delay. If every attempt fails, the API returns HTTP 503 with code `ai_unavailable` and the UI shows a temporary-busy message. Exhausted quota or billing limits return code `ai_quota_exceeded`, and a slow provider returns HTTP 504 with code `ai_timeout`.

### 2. Install backend dependencies

If `python` is available on `PATH`:

```powershell
Set-Location backend
python -m pip install -r requirements.txt
```

If Python is not on `PATH`, use the installed interpreter directly:

```powershell
& 'C:\Users\FALIHA FALAK\AppData\Local\Programs\Python\Python312\python.exe' -m pip install -r requirements.txt
```

### 3. Apply the database migration

Run from `backend`:

```powershell
python -m alembic upgrade head
```

This creates `backend/legalease.db` when using the default SQLite URL. The first application startup also synchronizes the built-in template definitions.

### 4. Start the API

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs` in development.

### 5. Start the frontend

In a second PowerShell window:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:3000` in a browser. Keep the frontend and API on the same hostname for local cookie authentication. If you open the frontend at `http://127.0.0.1:3000`, set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in `frontend/.env.local`. If you change the API URL or CSRF cookie name, place the matching `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_CSRF_COOKIE_NAME` values in `frontend/.env.local`; Next.js reads frontend environment files from that directory.

## Useful API endpoints

- `GET /health` — service, database, and provider status
- `GET /api/config` — non-secret provider configuration
- `POST /api/health/ai` — verify the selected provider without exposing its key
- `GET /api/templates` — list and filter templates
- `GET /api/templates/{slug}` — retrieve a template and its structured fields
- `POST /api/auth/register` — create an account
- `POST /api/auth/login` — create a signed session
- `POST /api/documents/generate` — generate a first draft
- `GET/PATCH/DELETE /api/documents/{id}` — manage owned documents
- `GET /api/documents/{id}/versions` — inspect version history
- `GET /api/documents/{id}/export/pdf` — download a PDF
- `GET /api/documents/{id}/export/docx` — download a DOCX
- `POST /api/assistant/chat` — ask a general-information question
- `POST /api/review` — review a supported uploaded document

Authenticated state-changing requests require the CSRF cookie and `X-CSRF-Token` header. Document access is scoped to the authenticated owner; administrator endpoints require the `admin` role.

## Verification commands

Backend:

```powershell
Set-Location backend
python -m pytest
python -m ruff check .
python -m compileall -q app tests
python -m alembic current
```

Frontend:

```powershell
Set-Location frontend
npm run typecheck
npm run lint
npm run build
```

The local verified configuration is SQLite. Mock AI covers deterministic drafting and review, while the assistant requires Gemini. The live Gemini check is intentionally separate from ordinary startup:

```powershell
$env:AI_PROVIDER='gemini'
$env:RUN_LIVE_AI_TESTS='1'
python -m pytest tests/test_providers.py -k live_gemini -q
```

## Project layout

```text
backend/
  app/
    api/routes/       FastAPI route modules
    providers/        Mock and Gemini provider implementations
    services/         Documents, exports, reviews, templates, and security helpers
    alembic/          Migration environment
  tests/              API and provider tests
  alembic.ini
  pyproject.toml
  requirements.txt
frontend/
  app/                App Router pages
  components/         UI, legal workflow, editor, and auth components
  lib/                API client and shared types
  eslint.config.mjs
  package.json
render.yaml
IMPLEMENTATION_STATUS.md
.env.example
```

## Deployment notes

- Set a long random `SECRET_KEY`.
- Set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- If the frontend and API are on different sites, set `SESSION_COOKIE_SAMESITE=none` together with `SESSION_COOKIE_SECURE=true`; otherwise keep `lax` for same-site deployments.
- Restrict `CORS_ORIGINS` to deployed frontend origins.
- Use a managed database and run `alembic upgrade head` during deployment.
- Keep Gemini credentials in the deployment secret store.
- Treat generated drafts and review findings as prompts for qualified legal review, not legal conclusions.
- `APP_ENV=production` refuses to start on an unsafe configuration: it requires a unique 32+ character `SECRET_KEY`, `SESSION_COOKIE_SECURE=true`, and at least one non-localhost `CORS_ORIGINS` entry.
- `DATABASE_URL` accepts the `postgres://` and `postgresql://` forms that managed providers hand out; it is rewritten to the `postgresql+psycopg://` driver, so `psycopg` must stay in `requirements.txt`.

## Deploying to Render and Vercel

The repository contains a `render.yaml` blueprint for the API and its PostgreSQL database. The frontend deploys separately to Vercel.

### 1. Push the repository

```powershell
git add .
git commit -m "Configure LegalEase for Render and Vercel deployment"
git push origin main
```

`.env` is ignored by git, so no local key is uploaded. Both platforms read secrets from their own dashboards.

### 2. Create the API on Render

1. In Render, choose **New > Blueprint**, select the repository, and apply `render.yaml`.
2. Render creates `legalease-db` and `legalease-api`, wires `DATABASE_URL` automatically, and generates a random `SECRET_KEY`.
3. Fill in the two `sync: false` values when prompted:
   - `GEMINI_API_KEY`: a freshly created key. Never reuse a key that was pasted into a chat, log, or commit.
   - `CORS_ORIGINS`: the exact frontend origin, for example `https://legalease.vercel.app`. Multiple origins are comma-separated.
   - `ADMIN_EMAILS`: comma-separated addresses that should receive the `admin` role.
4. Deploy. The start command runs `alembic upgrade head` before starting Uvicorn, so the schema and template seed are applied automatically.
5. Note the API URL, for example `https://legalease-api.onrender.com`, and confirm `https://legalease-api.onrender.com/health` returns `"status":"ok"`.

### 3. Deploy the frontend to Vercel

1. In Vercel, import the same repository and keep the root directory as `frontend`.
2. Add these environment variables for **Production** (and Preview if you want previews to work):
   - `NEXT_PUBLIC_API_URL`: the Render API URL, with no trailing slash.
   - `NEXT_PUBLIC_CSRF_COOKIE_NAME`: `le_csrf`.
3. Deploy. `NEXT_PUBLIC_API_URL` is inlined at build time, so changing it later requires a redeploy.

### 4. Re-check CORS after the first deploy

`CORS_ORIGINS` must match the Vercel domain exactly, including scheme and any `www` prefix. If the browser reports a CORS error, add the origin shown in the console to `CORS_ORIGINS` and let Render redeploy. If you attach a custom domain, add that origin as well.

### 5. Verify the live assistant

```powershell
$api = 'https://legalease-api.onrender.com'
Invoke-RestMethod -Method Post -Uri "$api/api/health/ai"
```

A `"verified": true` response confirms the deployed API can reach Gemini. Sign in on the Vercel URL, open **AI assistant**, and ask a question. Cross-site cookies work because the blueprint sets `SESSION_COOKIE_SAMESITE=none` with `SESSION_COOKIE_SECURE=true`; the frontend falls back to `GET /api/auth/csrf` because it cannot read the API-domain cookie from the Vercel origin.

### Free-tier limits to expect

- Render's free web service sleeps after inactivity, so the first request after a quiet period takes roughly 30-60 seconds while it starts.
- Render's free PostgreSQL instance expires after about 30 days and must be recreated or upgraded.
- `RATE_LIMITER` state is in-process, so rate limits apply per instance. Keep a single API instance or move the limiter to shared storage.
