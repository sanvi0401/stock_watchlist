# Smart Market Watch

> A production-ready stock watchlist and market-change intelligence dashboard built to answer one practical question: **what meaningfully changed since I last acknowledged a check?**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://stockmarketwatchlist-sanvi0401s-projects.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB?logo=react)](https://react.dev/)
[![Database](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00E599?logo=postgresql)](https://neon.tech/)

## Live Application

**Production:** https://stockmarketwatchlist-sanvi0401s-projects.vercel.app

The application is deployed on Vercel with a FastAPI API, React/Vite frontend, and PostgreSQL persistence through Neon.

---

## Overview

Smart Market Watch is a full-stack stock monitoring application designed around **acknowledged user baselines**, rather than treating every page refresh as a new observation.

The system combines:

- Personal stock watchlists
- Shared market-price snapshots
- User-specific acknowledged baselines
- Volatility-normalized change significance
- LIVE / DELAYED / STALE / UNAVAILABLE market-data states
- Explainable change detection
- In-app change history
- Dashboard notifications
- Secure authentication
- Google Authenticator / TOTP account protection and password recovery
- Production PostgreSQL persistence
- Request-driven refreshes suitable for serverless deployment

The goal is to surface **meaningful changes without manufacturing signals from ordinary page refreshes**.

---

## Key Features

### 📊 Personalized Watchlists

- Create and manage watchlists
- Add and remove stock symbols
- View current market information for tracked stocks
- Compare each stock against the user's acknowledged baseline

### 🔎 Meaningful Change Detection

The application scores market movement using multiple signals rather than a fixed percentage threshold:

- Volatility-standardized price movement
- Current volume compared with typical volume
- Short-term vs. longer-term realized volatility
- Configurable sensitivity: conservative, balanced, or sensitive

The result is a **0–100 significance score** and a severity classification.

### 🧠 Explainable Intelligence

The system is intentionally explainable rather than presenting an opaque "AI score".

Each detected change can include:

- Change type
- Significance score
- Severity
- Baseline price
- Current price
- Percentage movement
- Explanation
- Supporting evidence
- Detection timestamp

### 🕒 Correct "Last Checked" Semantics

A normal `GET /dashboard` request does **not** silently change the user's baseline.

The flow is:

1. The dashboard loads the user's acknowledged baseline.
2. Current shared market snapshots are retrieved.
3. The current market state is compared with that baseline.
4. Meaningful changes may be recorded idempotently.
5. The user explicitly acknowledges the current state.
6. `POST /dashboard/acknowledge` advances the baseline.

This prevents repeated page refreshes from hiding changes.

### 📚 Change History

The History page provides:

- Complete recorded change history
- Severity filtering
- Symbol filtering
- Cursor-based pagination
- Empty-state handling when no history exists

### 🔐 Authentication & Account Security

- JWT-based authentication
- Password hashing
- Token-version invalidation
- Secure password-reset handling
- Google Authenticator-compatible TOTP
- QR-code based authenticator setup
- Manual setup-key fallback
- Six-digit authenticator verification
- Authenticator-based password recovery

New users are guided through authenticator setup during onboarding before entering the main application.

### 📡 Market Data Status

The application explicitly communicates the quality and age of market data:

| Status | Meaning |
| --- | --- |
| **LIVE** | Provider reports live data and the quote is within the configured live-age window |
| **DELAYED** | Known delayed data that is still within the delayed-age window |
| **STALE** | Quote is older than the delayed-age window |
| **UNAVAILABLE** | No valid quote or usable snapshot is available |

The system does not silently turn provider failures into fake LIVE prices.

---

## Architecture

```text
                         ┌─────────────────────┐
                         │   React + TypeScript │
                         │       + Vite        │
                         └──────────┬──────────┘
                                    │
                              /api requests
                                    │
                         ┌──────────▼──────────┐
                         │       Vercel        │
                         │   Serverless API    │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │       FastAPI       │
                         │  Auth / Dashboard   │
                         │ Stocks / Watchlists │
                         │  Changes / Settings │
                         └───────┬───────┬─────┘
                                 │       │
                    ┌────────────┘       └──────────────┐
                    │                                   │
           ┌────────▼────────┐                 ┌────────▼────────┐
           │ Neon PostgreSQL │                 │  Market Data     │
           │   Persistent DB │                 │ Yahoo / Mock     │
           └─────────────────┘                 └─────────────────┘
```

### Market-data flow

```text
Market Provider
      ↓
Validate quote + determine data age
      ↓
Shared snapshot cache / market_snapshots
      ↓
Compare with user's acknowledged user_stock_state
      ↓
Calculate significance + severity
      ↓
Create idempotent DetectedChange / notification
      ↓
Dashboard + History
```

---

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite
- React Router
- Tailwind CSS
- Recharts
- qrcode.react
- Vitest

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Cryptography
- JWT authentication
- TOTP / RFC 6238-compatible authenticator codes
- Pytest

### Data & Infrastructure

- PostgreSQL / Neon
- Redis (optional)
- Vercel
- Yahoo market data
- Docker Compose for local infrastructure

---

## Application Areas

| Area | Purpose |
| --- | --- |
| `/login` | User authentication |
| `/register` | Account creation |
| `/onboarding` | Initial setup, watchlist creation and authenticator setup |
| `/app/overview` | Main market dashboard |
| `/app/watchlist` | Manage tracked stocks |
| `/app/history` | Review detected market changes |
| `/app/security` | Manage authenticator security |
| `/forgot-password` | Authenticator-based password recovery |
| `/reset-password` | Password reset flow |

---

## API

The backend is exposed under `/api` in production.

### Health & market

```text
GET  /api/health
GET  /api/market/session
```

### Authentication

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/forgot-password
POST /api/auth/recover-password
POST /api/auth/reset-password
```

### Authenticator

```text
POST /api/authenticator/setup
POST /api/authenticator/verify
GET  /api/authenticator/status
```

### Watchlists & dashboard

```text
GET  /api/watchlists
POST /api/watchlists
GET  /api/dashboard
POST /api/dashboard/acknowledge
```

### Stocks & history

```text
GET  /api/stocks/...
GET  /api/changes/history
```

### Internal refresh

```text
POST /api/internal/refresh-snapshots
```

The internal refresh endpoint requires the configured `X-Cron-Secret` and is intended for controlled scheduled refreshes.

---

## Data Model

The application separates shared market observations from user-specific state.

### `market_snapshots`

Stores reusable market observations so multiple users do not need independent copies of the same quote.

### `user_stock_state`

Stores the last **acknowledged** state for a user's stock.

### `detected_changes`

Stores meaningful changes detected against the user's acknowledged baseline.

### `users`

Stores account information, authentication state, and encrypted authenticator configuration.

This separation is central to the application's "last checked" behavior.

---

## Production Configuration

Production requires a persistent PostgreSQL database and a secure secret key.

Important environment variables include:

```env
ENVIRONMENT=production
SECRET_KEY=<secure-secret>
DATABASE_URL=<neon-postgresql-url>
MARKET_DATA_PROVIDER=yahoo
CORS_ORIGINS=<allowed-origins>
```

Optional infrastructure/configuration:

```env
REDIS_URL=<redis-url>
CRON_SECRET=<cron-secret>
SNAPSHOT_RETENTION_DAYS=14
LIVE_MAX_AGE_SECONDS=300
DELAYED_MAX_AGE_SECONDS=1200
```

Development can explicitly use:

```env
MARKET_DATA_PROVIDER=mock
```

Mock market data is never intended to be a silent production fallback.

---

## Local Development

### Backend

```bash
cd backend
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8765
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

Backend:

```bash
cd backend
PYTHONPATH=. pytest
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npm run build
```

### Docker

For local PostgreSQL and Redis:

```bash
docker compose up -d
```

---

## Production vs Development

| Capability | Development | Production |
| --- | --- | --- |
| Database | SQLite or PostgreSQL | PostgreSQL required |
| Secret key | Local placeholder permitted | Strong secret required |
| Market data | Mock or Yahoo | Yahoo / configured provider |
| Refresh | Background scheduler | Request-driven on Vercel |
| Redis | Optional | Optional with TTL fallback |
| CORS | Local origins | Explicit configured origins |
| Password recovery | Development helpers available | Secure production flow |
| Authenticator | Available | Recommended as part of onboarding |

---

## Security Design

The application includes several defensive controls for production use:

- Passwords are hashed rather than stored in plaintext.
- JWT sessions can be invalidated through token-version changes.
- Password-reset tokens are hashed, expire, and are single-use.
- Production rejects weak/insecure `SECRET_KEY` configuration.
- Authenticator secrets are encrypted at rest using a key derived from the application secret.
- TOTP verification accepts a small clock-skew window.
- CORS is explicitly configured rather than allowing every Vercel domain.
- Provider failures do not create fabricated LIVE market prices.

**Never commit production secrets, database credentials, API keys, or `.env` files to Git.**

---

## Intentional Limitations

- Yahoo market data can be delayed; the application does not claim exchange-grade real-time data.
- The US market session calendar is an approximation and is not a licensed exchange calendar.
- The application does not provide dark-pool data, event-calendar intelligence, or FX conversion.
- In-app notifications are application records rather than guaranteed email/push delivery.
- Redis is optional; fallback caching is process-local.
- Snapshot retention defaults to 14 days.

---

## Project Structure

```text
stock_watchlist/
│
├── api/
│   └── index.py                 # Vercel API entry point
│
├── backend/
│   ├── app/
│   │   ├── routers/             # API routes
│   │   ├── market/              # Market data and session logic
│   │   ├── intelligence/        # Significance/change detection
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── security.py           # Auth + TOTP security
│   │   ├── db.py                 # Database setup/schema compatibility
│   │   ├── config.py             # Application configuration
│   │   └── main.py               # FastAPI application
│   │
│   └── tests/                   # Backend tests
│
├── frontend/
│   ├── public/                  # Static assets
│   └── src/
│       ├── components/          # Reusable UI components
│       ├── layouts/             # Application layouts
│       ├── pages/               # Application pages
│       └── services/            # API client
│
├── .env.example
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── vercel.json
└── README.md
```

---

## Deployment

The production application is deployed using **Vercel**.

### Deployment architecture

```text
GitHub main
    ↓
Vercel deployment
    ↓
React/Vite frontend
    +
FastAPI serverless API
    ↓
Neon PostgreSQL
```

Production environment variables are configured in Vercel rather than committed to the repository.

### Production URL

**https://stockmarketwatchlist-sanvi0401s-projects.vercel.app**

---

## Design Principles

### Business first. Signal second. Technology third.

The application is designed around a user problem rather than simply exposing stock prices.

Instead of asking:

> "What is the stock price right now?"

it asks:

> **"What changed, how significant is it, and has the user already acknowledged it?"**

That principle drives the data model, change-detection logic, dashboard behavior, and history system.

---

## Status

**Production deployment:** Live

**Primary stack:** React + TypeScript + FastAPI + SQLAlchemy + PostgreSQL/Neon + Vercel

**Market data:** Yahoo / explicitly configured provider

**Authentication:** JWT + Google Authenticator-compatible TOTP

---

## Author

**Sanvi Devnani**

GitHub: https://github.com/sanvi0401

Repository: https://github.com/sanvi0401/stock_watchlist
