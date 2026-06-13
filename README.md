# 🏃🚴🏋️ ripe_fitness

A personal AI fitness coach. It reads your **Garmin** data, knows your **weekly
availability** and **target event**, and uses **Claude** to generate and adapt a
week of running, cycling (Zwift), and gym sessions — shown in-app as structured
workouts with targets and rationale.

Built for a single user (you). Goal anchor: **Sydney Marathon, sub-3:00**.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + SQLAlchemy (Python 3.13, `uv`) |
| Frontend | React + TypeScript (Vite) |
| Database | SQLite locally · Postgres on Railway |
| Data | `garminconnect` (unofficial Garmin Connect library) |
| Coach | Claude API (forced structured tool output) |
| Hosting | Railway (two services + Postgres) |

```
ripe_fitness/
├── backend/          FastAPI API
│   ├── app/
│   │   ├── main.py          app + CORS + table creation
│   │   ├── config.py        env settings (DB URL normalization, CORS)
│   │   ├── models.py        Profile, Availability, Event, Activity, DailyMetric, Plan, Workout
│   │   ├── auth.py          single-user bearer-token guard
│   │   ├── routers/         auth, profile, availability, events, activities, plan
│   │   └── services/        garmin_sync · metrics (featurization) · coach (Claude)
│   └── Dockerfile
└── frontend/         React dashboard
    ├── src/ (App, Login, Dashboard, api client)
    └── Dockerfile
```

---

## Local development

### Backend
```bash
cd backend
cp .env.example .env          # then fill in secrets (see below)
uv sync
uv run uvicorn app.main:app --reload --port 8000
# API at http://localhost:8000  ·  docs at http://localhost:8000/docs
```

The DB defaults to a local SQLite file — no Postgres needed for dev.

### Frontend
> Requires **Node.js 20+** (not currently installed on this machine — see note below).
```bash
cd frontend
cp .env.example .env          # VITE_API_URL=http://localhost:8000
npm install
npm run dev                   # http://localhost:5173
```

### Environment variables (`backend/.env`)
| Var | Purpose |
|---|---|
| `DATABASE_URL` | SQLite locally; Railway injects Postgres automatically |
| `APP_PASSWORD` | password you type to log in |
| `APP_API_TOKEN` | bearer token the frontend stores after login |
| `ANTHROPIC_API_KEY` | your Claude API key |
| `ANTHROPIC_MODEL` | default `claude-sonnet-4-6` |
| `GARMIN_EMAIL` / `GARMIN_PASSWORD` | Garmin Connect login |
| `GARMIN_TOKEN_STORE` | dir for cached OAuth tokens (avoids re-login) |
| `CORS_ORIGINS` | comma-separated allowed frontend origins |

---

## API surface

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | liveness (no auth) |
| POST | `/auth/login` | `{password}` → `{token}` |
| GET/PUT | `/profile` | FTP, threshold pace, HR, weight |
| GET/POST/DELETE | `/availability` | weekly recurring slots |
| GET/POST/DELETE | `/events` | target events |
| GET | `/activities` | recent synced activities |
| POST | `/activities/sync` | pull from Garmin |
| GET | `/plan/latest` | most recent generated plan |
| POST | `/plan/generate` | ask Claude for this week's plan |
| GET | `/plan/context` | the featurized data the coach reasons over |
| PATCH | `/plan/workout/{id}` | mark a workout done/skipped |

All routes except `/health` and `/auth/login` require `Authorization: Bearer <token>`.

---

## Deploying to Railway

This is a **monorepo with two services** plus a Postgres plugin.

1. **Create a Railway project** and connect this GitHub repo.
2. **Add Postgres**: *New → Database → PostgreSQL*. Railway auto-injects
   `DATABASE_URL` into services in the project.
3. **Backend service**: *New → GitHub repo*, set **Root Directory = `backend`**.
   Railway detects the Dockerfile. Add variables:
   `APP_PASSWORD`, `APP_API_TOKEN`, `ANTHROPIC_API_KEY`, `GARMIN_EMAIL`,
   `GARMIN_PASSWORD`, and `CORS_ORIGINS` (= your frontend URL, set after step 4).
   Reference the Postgres `DATABASE_URL` variable.
4. **Frontend service**: *New → GitHub repo*, set **Root Directory = `frontend`**.
   Add build variable `VITE_API_URL` = the backend service's public URL.
5. Set the backend's `CORS_ORIGINS` to the frontend's public URL and redeploy.

> **Garmin + cloud note:** the unofficial library logs in with your credentials.
> From a datacenter IP, Garmin may issue an MFA/captcha challenge. Tokens are
> cached in `GARMIN_TOKEN_STORE` so login happens rarely. If the cloud login is
> blocked, the fallback is to run the sync from a trusted IP (e.g. your PC) to
> seed the token store, then deploy with those tokens.

---

## Build status & roadmap

- [x] **Phase 0** — scaffold, auth, DB, deploy config *(this commit)*
- [x] **Phase 1** — Garmin sync pipeline (activities + daily wellness)
- [x] **Phase 2** — profile, availability, events
- [x] **Phase 3** — Claude coach: featurized context → structured weekly plan
- [ ] **Phase 4** — scheduled auto-sync, load/form charts, recovery-aware regen,
      availability editor UI, mobile polish

> Phases 1–3 are wired end-to-end at the API level. The frontend currently
> surfaces goal, markers, Garmin sync, and the weekly plan; the availability
> **editor UI** and richer charts are the main Phase 4 frontend work.
