# Tandem product specification

Tandem helps people understand spending, plan purchases, and share savings achievements. It is a responsive multi-user web application with simulated finances and individual account ownership.

## Architecture

React, TypeScript, Vite, Tailwind CSS, shadcn/ui configuration, React Router, and Lucide provide the client. FastAPI routers call backend services using Pydantic schemas and SQLAlchemy sessions. Alembic manages schema changes. SQLite supports local development. A configured SQLAlchemy URL allows later PostgreSQL adoption.

## Phase 0

Provide registration, login, current-user lookup, health monitoring, and a private workspace. Use Argon2 hashes, short-lived signed JWTs, unique emails and usernames, and server-side identity checks. The database contains users and a user-owned virtual bank account structure with integer minor-unit balances. Phase 0 leaves account provisioning and financial operations for Phase 1.

Home is private. Simulator, MoneyLeaks, Explore, and Community have navigable placeholders that explain planned capabilities. Financial data appears only when populated by working application features.

## Roadmap

1. Virtual banking, transaction records, and private dashboards.
2. Savings goals and purchase simulation with deterministic projections.
3. Transaction audits, recurring expense detection, and MoneyLeaks.
4. Community profiles and posts, reactions, and comments.
5. Banknote histories and messages, plus nearby deal discovery.
6. End-to-end testing and deployment.

Optional AI explanations use minimal structured data server-side and supplement deterministic calculations. Deal and map integrations can be added behind backend services as their phases require.
