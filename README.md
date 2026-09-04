# Smart Market Watch

**What meaningfully changed since I last checked, and what deserves my attention now?**

A watchlist that remembers what *you* saw. Every symbol you follow has a per-user
baseline (the price on your previous visit). When you come back, the Overview
compares today's quote to that baseline, scores the move against the stock's own
volatility and volume, and explains in plain English why it matters. Quotes are
always labelled LIVE / DELAYED / STALE / UNAVAILABLE, and a provider outage never
overwrites good data.

Built for **Code, by Groww 2026** (Smart Market Watchlist). The 100-word pitch is
in [PITCH.md](PITCH.md).

---

## Run it

Requirements: Python 3.12, Node 20+. No database server needed.

```bash
# backend  → http://127.0.0.1:8765  (SQLite file, delayed Yahoo Finance quotes)
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8765
```

```bash
# frontend → http://127.0.0.1:43123  (proxies /api → backend)
cd frontend && npm install && npm run dev
```

Open the frontend, sign up, finish onboarding (it creates a first watchlist),
and open Overview. Come back later, or click **I'm caught up** and re-add a name,
to see the "since you last checked" comparison in action.

Offline / deterministic demo: `MARKET_DATA_PROVIDER=mock`. The mock universe
seeds a 14-hour-old baseline so the first Overview already shows changes.

Tests:

```bash
cd backend && PYTHONPATH=. pytest          # 55 tests
cd frontend && npm test && npm run lint && npm run build
```

All configuration is in [.env.example](.env.example). Postgres and Redis are
optional (`docker compose up -d`), used automatically when `DATABASE_URL` /
`REDIS_URL` point at them.

---

## Problem interpretation

The brief says "track stocks" is table stakes; the product is the *diff*. Three
decisions follow from that:

1. **The baseline is personal and it is a visit, not a request.**
   "Since you last checked" means since the last time you *looked*, so the
   baseline is per user, per symbol, stored server-side, and it only moves when
   you open the Overview. Reloading the page a minute later is the same visit
   (`CHECK_SESSION_MINUTES`, default 10), so a refresh cannot erase what you
   were just shown. Viewing a stock page or a watchlist table is read-only and
   never moves the baseline. **I'm caught up** resets every baseline on demand.

2. **"Meaningful" is relative to the stock, not a fixed percent.**
   A 2% move is a quiet day for TSLA and a big one for Costco. The move is
   measured in units of the stock's own typical daily move (60-day realised
   volatility). Volume can corroborate a move but cannot create one: a flat
   price on heavy volume is not "something changed since you looked".

3. **Say what you don't know.**
   Every quote carries a freshness label derived from market hours and print
   age, not from what the provider claims. When the provider fails, the last
   good snapshot is served and labelled STALE. When there is nothing valid,
   the symbol is listed as UNAVAILABLE with the last price you saw, and your
   baseline is left untouched.

### What the Overview shows

| Section | Rule |
|---|---|
| Needs your attention | HIGH significance since your previous visit |
| Meaningful changes | MEANINGFUL or NOTABLE |
| No significant change | STABLE, plus names seen for the first time ("baseline set") |
| Unavailable | no valid quote; last seen price shown, baseline preserved |

Each card carries the score, the plain-language explanation, and the evidence
used (move in %, move in typical-day units, volume ratio, feed status).

---

## Architecture

Modular monolith: FastAPI + SQLAlchemy backend, React + TypeScript + Vite
frontend, one shared market-data path.

```
frontend/src            React pages (Overview, Watchlists, Discover, Stock, History, Settings)
backend/app
  routers/              auth, watchlists, dashboard (+ /checkpoint), stocks, changes, settings
  intelligence/
    last_seen.py        visit semantics: baseline / last-seen state machine, change ledger
    significance.py     scoring in volatility units, sensitivity bands
    explanation.py      plain-English "why" + evidence
  market/
    service.py          cache → provider → validate → resolve conflicts → snapshot
    freshness.py        market hours, LIVE/DELAYED/STALE rules, daily-bar timestamps
    yfinance_provider   delayed Yahoo quotes (local), yahoo_http (Vercel, no pandas),
    mock.py             deterministic offline universe, alpha_vantage optional
  worker.py             background refresh of every watched symbol + snapshot pruning
  cache.py              Redis if reachable, else in-process TTL cache
```

### Data model

- `users`, `watchlists`, `watchlist_stocks` (unique per list + symbol)
- `market_snapshots` — **shared across users**. One row per distinct print;
  unchanged prints refresh the row in place. Newest row per symbol is the
  outage fallback. Pruned after 7 days.
- `user_stock_state` — per (user, symbol): `baseline_price/at` (what we compare
  against) and `last_seen_price/at` (most recent viewing). Unique constraint;
  concurrent first views are resolved by the constraint, not by hoping.
- `detected_changes` — the ledger. Written **once per visit per symbol**, only
  when the baseline actually rolled and the move cleared the NOTABLE floor.
- `notifications` — in-app alerts, created alongside HIGH/MEANINGFUL ledger rows.

### Request flow for `GET /dashboard`

1. Collect the user's distinct symbols; batch-prefetch anything not cached
   (one provider call per 50 symbols, shared by every user watching them).
2. Load all `user_stock_state` rows in one query.
3. Per symbol: get quote (cache → provider → last snapshot as STALE), decide
   whether this is a new visit, score against the baseline, explain, and if a
   new visit and the move is notable, append to the ledger.
4. Roll `last_seen` forward, sort by severity then score, and return.
   One failing symbol is reported as UNAVAILABLE; it never fails the request.

### Scoring

```
z         = |move %| / daily volatility           (how many "typical days" the move is)
price     = z / 2.5 × 100                          (2.5 typical days = 100)
volume    = (volume / 60-day average − 1) / 1.5 × 100
score     = 0.8 × price + 0.2 × volume × min(1, z)
```

Balanced bands: STABLE < 30 ≤ NOTABLE < 60 ≤ MEANINGFUL < 80 ≤ HIGH.
Conservative and Sensitive scale the score and shift the bands. A 1-sigma move
is NOTABLE, 2-sigma is MEANINGFUL, 2.5-sigma (or 2-sigma on heavy volume) is HIGH.

### Freshness

| Label | When |
|---|---|
| LIVE | provider is real-time and the print is under 5 minutes old |
| DELAYED | delayed feed (Yahoo ≈ 15 min) but current for the session; any print while the market is closed |
| STALE | market open and the newest print is older than `STALE_AFTER_MINUTES`; or a fallback snapshot is being served |
| UNAVAILABLE | nothing valid |

Daily-bar providers stamp today's bar with the fetch time (it is still being
updated) and a finished bar with that session's 16:00 ET close, so weekend
data is DELAYED, not STALE.

### Conflicting and bad data

- Prints with non-positive or NaN prices, negative volume, impossible
  volatility, or timestamps in the future are rejected or clamped in one place
  (`market/service._validate`).
- A snapshot never moves backwards: if a provider returns an older print than
  the one stored (retry storms, a lagging replica, mixed providers), the stored
  one wins and is served.
- Labels are recomputed at read time. A cached "LIVE" quote is re-classified
  against the clock, so a cache never lies about freshness.

---

## Scaling

- **Cost grows with distinct symbols, not users × symbols.** Snapshots and the
  quote cache are shared; the background worker refreshes every watched symbol
  once per interval. Ten thousand users watching NVDA cost one fetch per
  interval.
- Per-user work is O(symbols on the dashboard) with two queries (watchlists,
  states) plus cache reads. Watchlists are capped at 100 symbols each.
- State is in the database, not in process memory, so the API runs behind
  multiple workers or instances. Redis is optional; the in-process cache has
  the same TTL semantics.
- History uses keyset pagination on the ledger id.

Next steps at real scale: move the refresh worker to its own process, key the
cache by provider *and* freshness window, and add a per-user rate limit on
`/dashboard`.

---

## Edge cases handled (and tested)

- First observation never claims a change. Adding a symbol records the price
  you saw as the baseline.
- Refresh inside a visit keeps the baseline; a new visit rolls it. React Strict
  Mode's double fetch is a non-issue by design, not by an in-memory hack.
- Ledger and notifications are written once per visit, not per request.
- Concurrent first-view or duplicate-add requests are resolved by unique
  constraints and return 409, not 500.
- SQLite returns naive datetimes; everything is normalised to UTC before
  comparison.
- The in-process cache expires (the previous version froze prices forever when
  Redis was down).
- Unknown timezones and invalid sensitivity/lookback values are rejected with
  4xx and a message the UI can show.
- Password reset tokens are hashed at rest, single-use, and expire in 2 hours.
  Forgot-password returns the same shape whether or not the address exists.

---

## Deliberate simplifications

- **No migrations.** Schema is created with `create_all`; it is a hackathon
  build. Alembic is the obvious next step. If you upgrade from an older
  database, delete `backend/marketwatch.db`.
- **No email.** Outside `ENVIRONMENT=production` the reset link is returned in
  the response so the flow can be exercised.
- **Stateless JWT logout.** The client discards the token; there is no
  server-side denylist.
- **US market hours only, no holiday calendar.** A US holiday shows as OPEN
  and quotes will read STALE for the day. Quotes are USD.
- **Yahoo's unofficial endpoints** can throttle. Every provider falls back to the
  last snapshot, then to the deterministic mock universe for well-known names.
- **Vercel.** The API deploys as a serverless function (`api/index.py`). Without
  `DATABASE_URL` it uses SQLite in `/tmp`, which is wiped when the instance
  recycles; the UI shows a banner and `/health` reports `persistence:
  ephemeral`. Point `DATABASE_URL` at a hosted Postgres for a durable demo.

---

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register`, `/auth/login`, `/auth/forgot-password`, `/auth/reset-password` | accounts |
| GET | `/auth/me` | current user |
| GET/POST | `/watchlists` | list (with quotes and counts) / create |
| GET/PATCH/DELETE | `/watchlists/{id}` | one list |
| POST/DELETE | `/watchlists/{id}/stocks[/{symbol}]` | add by name or ticker / remove |
| GET | `/dashboard` | the Overview; counts as a visit |
| POST | `/dashboard/checkpoint` | "I'm caught up": reset all baselines |
| GET | `/stocks/search?q=` | company name or ticker |
| GET | `/stocks/{symbol}` | briefing; read-only, does not move the baseline |
| GET | `/changes/history?severity=&symbol=&cursor=` | ledger, keyset paginated |
| GET/PATCH | `/settings` | name, timezone, sensitivity, baseline mode, overview filter |
| GET/POST | `/notifications`, `/notifications/read` | in-app alerts |
| GET | `/health` | provider, cache tier, persistence mode, market state |

Errors are `{code, message}` with a stable `code` the frontend switches on.
