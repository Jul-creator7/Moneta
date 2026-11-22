# Tandem

Tandem is a personal finance and social savings web app. It uses simulated finances.

## Local development

Use Python 3.11+ and Node.js 22.12+ with npm. Start the API from the repository root.

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -c 'import secrets; print("JWT_SECRET=" + secrets.token_hex(32))' >> .env
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

Run the setup commands once. Keep the same local secret across restarts to preserve existing sessions until they expire.

Start the web app in a second terminal from the repository root.

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. FastAPI documentation is at http://127.0.0.1:8000/docs. Vite proxies `/api` to the local backend. For deployment, serve `/api` through the same origin or set `VITE_API_BASE_URL` to the API origin before building and configure the backend's `CORS_ORIGINS`. The web host needs SPA fallback for direct visits to application routes.

## Verification

```sh
# From backend with the virtual environment active
alembic check
python -m pytest -q

# From frontend
npm run build
```

## Accounts and sessions

Registration creates a private user profile. Sign in with the email and password used during registration. Passwords are hashed with Argon2. The browser stores a 30-minute bearer token in local storage for refresh persistence. Scripts running on the same origin can read that token. Logout clears local storage and the browser's session state. An issued token remains valid until expiration. Before a public deployment, revisit session storage, revocation, login throttling, and HTTPS.

SQLite is the local default. Set `DATABASE_URL` to use a different database and install its SQLAlchemy driver. Test the migrations on that database before deployment.
