# Smart Market Watch

This is not a generic stock ticker. The product answers:

**What meaningfully changed since I last acknowledged a check, scored against each name’s own recent behavior?**

Shared market snapshots are compared to a per-user **acknowledged** baseline. A GET does not quietly redefine “last checked.” Volatility-normalized significance, explicit LIVE / DELAYED / STALE / UNAVAILABLE labels, and “first observation = baseline, not a fake move” are the core.

## Architecture

```
Provider (Yahoo delayed, or mock when explicitly configured)
    → validate + age-based status
    → shared snapshot cache + persisted market_snapshots
    → dashboard compares vs user_stock_state (acknowledged last-seen)
    → POST /dashboard/acknowledge advances the baseline
```

- **Frontend:** React + TypeScript + Vite + Tailwind (`frontend/`)
- **Backend:** FastAPI + SQLAlchemy (`backend/`)
- **Database:** PostgreSQL in production (`DATABASE_URL`). SQLite is **local development / tests only**.
- **Redis:** optional quote cache; in-memory fallback **with TTL**.
- **Quotes:** delayed Yahoo. Local default `MARKET_DATA_PROVIDER=yfinance`. On Vercel (`VERCEL=1`) Yahoo HTTP (`yahoo_http.py`) so the function stays small. `mock` only when that provider is set on purpose. Provider failure never invents a LIVE print: last valid snapshot is returned as DELAYED/STALE by age, otherwise UNAVAILABLE.

## What “last checked” means

`user_stock_state` is the last **acknowledged** snapshot, not the last HTTP GET.

1. `GET /dashboard` loads that baseline, fetches current shared quotes, scores the delta, and may record an idempotent `DetectedChange` / in-app notification (same fingerprint → no duplicate). It does **not** update last-seen.
2. `POST /dashboard/acknowledge` writes current prices into `user_stock_state`.
3. Opening a stock page or watchlist calculates the same comparison and does **not** write change history.

First observation (no baseline): we show the quote and say so. We do not claim a since-last-check move.

## Significance (explainable, not “AI”)

Score 0–100 from:

- **Volatility-standardized move** — `|return| / recent daily-return stdev` (not a mean-adjusted z-score)
- **Volume vs typical**, scaled by how far through the US regular session we are (conservative when the session has barely started; we do not have true volume-by-time-of-day)
- **Short vs longer realized vol** (about 5 sessions vs up to 30) when enough history exists — a relative regime, not a 1.8% constant

Sensitivity (conservative / balanced / sensitive) only changes classification bands. Watchlist membership does not add bonus points.

## Data status (configurable)

| Status | Meaning |
| --- | --- |
| LIVE | Provider marked live **and** quote age ≤ `LIVE_MAX_AGE_SECONDS` (default 5 minutes) |
| DELAYED | Known delayed, still within `DELAYED_MAX_AGE_SECONDS` (default 20 minutes) |
| STALE | Older than the delayed window (applies to formerly LIVE or DELAYED prints) |
| UNAVAILABLE | No valid quote and no usable snapshot |

US session PRE / OPEN / CLOSED is an **approximate** regular-hours calendar (weekends + a small holiday set), not a licensed exchange feed.

## Production vs development

| | Development | Production |
| --- | --- | --- |
| `SECRET_KEY` | Local placeholder allowed if unset | Process **exits** unless ≥ 32 chars and not a known insecure string |
| `DATABASE_URL` | SQLite file or Postgres | **Postgres required.** `/tmp` SQLite is rejected |
| Password reset | May echo `dev_reset_token` when `ENVIRONMENT=development\|test` and **not** on Vercel | Generic success only; email if SMTP is set; never return the token |
| Mock quotes | `MARKET_DATA_PROVIDER=mock` | Do not use mock as a silent fallback |
| Demo last-seen seed | Mock provider may seed an old baseline so the first screen shows a delta | Yahoo path never invents a prior observation |
| Refresh | Local APScheduler | **Request-driven** on Vercel (no always-on worker). Optional `POST /internal/refresh-snapshots` with `X-Cron-Secret` if `CRON_SECRET` is set |
| CORS | Local origins | Explicit `CORS_ORIGINS` plus this deployment’s `VERCEL_URL` — not `*.vercel.app` |

Password reset tokens are hashed, expire in 2 hours, and are single-use. Reset increments `token_version` so existing JWTs stop working.

## Setup

```bash
docker compose up -d   # Postgres + Redis if you use Compose
cp .env.example backend/.env
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

cd backend && PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8765
cd frontend && npm run dev   # http://127.0.0.1:43123
```

### Tests

```bash
cd backend && PYTHONPATH=. pytest
cd frontend && npm test && npm run build
```

## Intentional limitations

- Yahoo quotes are **delayed**. We do not claim a dark pool, event calendar, or FX conversion.
- In-app notifications are preference-gated records, not email/push delivery (unless you add SMTP for password reset only).
- Snapshot rows older than `SNAPSHOT_RETENTION_DAYS` (default 14) are pruned on refresh.
- Circuit/cooldown on provider 429 is per-process (Redis if available), not a global mesh.

## Folder structure

```
backend/app/           API, models, market, intelligence
backend/tests/         pytest
frontend/src/pages     routes
```
