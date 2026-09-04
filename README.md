# Smart Market Watch

This is not a generic stock watchlist. The product answers:

**What meaningfully changed since I last checked, and what deserves my attention now?**

It remembers each user’s last-seen price, compares it to a shared market snapshot, scores the move against that name’s own volatility and volume, and explains why it matters. Live vs delayed vs stale vs unavailable is always explicit.

## Architecture

Modular monolith:

- **Frontend:** React + TypeScript + Vite + Tailwind + React Router (`frontend/`)
- **Backend:** FastAPI + SQLAlchemy (`backend/`)
- **PostgreSQL:** users, watchlists, shared `market_snapshots`, `user_stock_state`, `detected_changes`
- **Redis:** latest quote cache (in-memory fallback if Redis is down)
- **MarketDataService → MarketDataProvider:** delayed Yahoo Finance quotes. Locally this uses `yfinance` when `MARKET_DATA_PROVIDER=yfinance`. On Vercel it uses Yahoo’s public chart API (`httpx` only) so the serverless function stays under the size limit. Mock fallback if Yahoo fails. Alpha Vantage when `MARKET_DATA_PROVIDER=alpha_vantage` and `ALPHA_VANTAGE_API_KEY` is set
- **Intelligence:** `backend/app/intelligence/` (`significance.py`, `explanation.py`, `last_seen.py`)

Last-seen flow: load previous `user_stock_state` → fetch current snapshot → compare → score → explain → return → then update last seen. First observation never claims a change. Unavailable quotes never overwrite a valid previous price.

## Stitch

Visual language is taken from the Stitch project **Market Watch Intelligence Platform** (dark navy surfaces, Inter + JetBrains Mono, indigo intelligence accent, green/red delta pills). Login, forgot/reset, and onboarding screens were not in Stitch; they reuse the same tokens.

## Setup

```bash
# Postgres + Redis (Docker) or local installs
docker compose up -d

cp .env.example backend/.env   # or export the vars

python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend && npm install && cd ..
```

Create DB user/database `marketwatch` / `marketwatch` if not using Compose.

### Environment

See `.env.example`. Never commit `.env`.

- `MARKET_DATA_PROVIDER=yfinance` — delayed Yahoo Finance quotes locally (`pip install yfinance`)
- `MARKET_DATA_PROVIDER=yahoo_http` — delayed Yahoo chart/search HTTP APIs (used automatically on Vercel)
- `MARKET_DATA_PROVIDER=mock` — deterministic terminal quotes (no network)
- `MARKET_DATA_PROVIDER=alpha_vantage` + `ALPHA_VANTAGE_API_KEY` — delayed live quotes, mock search fallback if the provider misses

### Run

```bash
# backend  http://127.0.0.1:8765
cd backend && PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8765

# frontend http://127.0.0.1:43123  (proxies /api → backend)
cd frontend && npm run dev
```

Sign up, complete onboarding (default tickers NVDA/AAPL/MSFT/TSLA), then open Overview. Mock names are seeded with a 14-hour-old baseline so the first dashboard visit already shows last-checked deltas.

### Vercel

Frontend (Vite) and backend (FastAPI) deploy together. `vercel.json` builds `frontend/dist` and routes `/api/*` to `api/index.py`.

On Vercel the API uses SQLite in `/tmp` unless you set `DATABASE_URL` (Postgres). `/tmp` is wiped when the serverless instance recycles, which is why a later login used to say “email or password is incorrect” even after a successful sign-up. The browser now keeps an encrypted account backup (`mw_identity` in localStorage) and the API restores the user on login, `/me`, and forgot-password. Sessions last 30 days; even an expired JWT is recovered from that backup on this device. Use a durable Postgres URL in production if you need the same account on other browsers.

Forgot password does not send email (no SMTP on this demo). Submit the address on `/forgot-password` and use the reset link shown on the page.

Add stocks by company name (“Google”) or ticker (GOOGL) from Discover (Add on the right of each result), a watchlist, or the global search box.

```bash
npx vercel --prod
```

### Tests

```bash
cd backend && PYTHONPATH=. pytest
cd frontend && npm test && npm run build
```

### Demo

1. Open the landing page → Sign Up  
2. Onboarding creates a watchlist  
3. Overview ranks **Needs attention → Meaningful → Stable** by significance, not raw %  
4. Stock detail shows last-check delta, why it matters, evidence, chart, feed status  
5. Change history is persisted and filterable  

## Folder structure

```
backend/app/           API, models, market, intelligence
backend/tests/         pytest
frontend/src/pages     routes
frontend/src/components
frontend/src/services/api.ts
```
