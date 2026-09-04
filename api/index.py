"""Vercel serverless entry: FastAPI app with /api prefix stripped."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db import Base, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

Base.metadata.create_all(bind=engine)


class StripApiPrefix:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            path = scope.get("path", "")
            if path.startswith("/api"):
                scope = dict(scope)
                stripped = path[4:] or "/"
                scope["path"] = stripped
                scope["raw_path"] = stripped.encode()
        await self.app(scope, receive, send)


app = StripApiPrefix(fastapi_app)
