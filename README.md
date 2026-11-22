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

## Virtual banking

Home contains personal chequing and savings accounts in simulated Canadian dollars. Migrations provision both accounts for existing users, and registration provisions them for new users. Run `alembic upgrade head` with the API stopped when updating a Phase 0 installation.

Add simulated deposits, record income, pay bills, record purchases, and transfer funds between accounts. The monthly dashboard uses UTC calendar months. Income counts recorded income, spending counts purchases and bills, and the savings rate is (income minus spending) divided by income when income exists. Deposits and transfers are excluded from monthly income and spending.

Load demo data into empty accounts from Home. Reset clears the signed-in user's simulated balances and transaction history after confirmation. Transaction amounts use integer cents. Internal transfers create matched debit and credit entries in a single database transaction.

## Savings goals and purchase simulator

In **Simulator**, create a goal with a target amount, an optional target date, and a planned contribution. Transfer simulated money into savings on **Home** and reserve it by setting the goal's total allocation. Lower the allocation to release it. Purchases, bills, and transfers from savings cannot use funds reserved for goals. Resetting the banking simulation clears allocations and keeps goal plans.

The purchase comparison estimates two timelines using the goal's allocated amount and planned contribution. The first contribution lands 30 days after the estimate date in UTC, and each subsequent contribution lands 30 days later. The purchase can reduce the goal's allocation immediately or divert upcoming contributions until the purchase amount is covered. An already-funded goal stays complete when the purchase only diverts future contributions. A zero contribution leaves an unfinished goal without an estimated completion date. Comparing a purchase leaves all accounts and allocations intact.

## Purchase audits and MoneyLeaks

After a simulated purchase, choose **Audit this purchase** or use its audit link in Home's transaction history. Save a necessity rating from 1 to 10 and an optional private reflection. You can revisit and edit saved audits on **MoneyLeaks**. Suggestions are general options based on the purchase category. The goal estimate models the purchase cost as diverted upcoming contributions. Resetting the simulation clears the associated audits.

MoneyLeaks reviews the last 365 UTC calendar days. It groups expense charges by normalized merchant name and category, looks for at least three similar charges on separate dates, and allows 5–9 days for weekly gaps and 25–35 days for monthly gaps. It annualizes the latest amount at 52 or 12 charges per year. Patterns with no charge within 14 or 50 days, respectively, are excluded from potential savings. Possible duplicates share a normalized merchant, amount, and UTC date. The estimates are prompts to review the charges and verify cancellation terms.

To see sample recurring charges, a price increase, and a possible duplicate, use **Load demo data** from an empty simulation.
