# SearchInCircle

Trust-circle discovery platform: publishers build a trusted circle, tag skills/resources on
themselves and people they know, post requirements, and get AI-ranked matches surfaced within
their direct circle only.

Spec and ticket breakdown: see GitHub issue #1 and its sub-issues.

## Structure

Two independent apps, each with its own dependencies and its own README:

- `frontend/` — React Native (Expo) mobile app. See `frontend/README.md` and `frontend/AGENTS.md`.
- `backend/` — NestJS modular monolith API (Prisma + PostgreSQL/pgvector). See `backend/README.md`.

`docs/` holds the original PRD and architecture documents. `docs/agents/` holds this repo's
issue-tracker and domain-doc conventions for coding agents.

## Local setup

### Backend

```bash
cd backend
npm install
cp .env.example .env   # fill in the real AWS RDS DATABASE_URL
npx prisma generate
npm run start:dev
```

`GET /health` reports `{ status: "ok", database: "reachable" }` once `DATABASE_URL` points to a
real, reachable Postgres instance. The pgvector extension migration
(`prisma/migrations/20261030000000_enable_pgvector`) needs `npx prisma migrate deploy` run against
that database before it's enabled — this requires a role with `rds_superuser` (the RDS master user
has it by default).

### Frontend

```bash
cd frontend
npm install
npx expo start
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) builds and tests both apps on every push and PR.
