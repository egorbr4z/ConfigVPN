"""FastAPI application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing from the repo root (core/, data/)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.storage import JSONStorage
from routers import auth, plans, providers, payments, subscriptions, referrals
from routers.admin import users as admin_users
from routers.admin import plans as admin_plans
from routers.admin import payments as admin_payments
from routers.admin import providers as admin_providers
from routers.admin import settings as admin_settings

DATA_DIR = ROOT / "data"

storage = JSONStorage(DATA_DIR)

app = FastAPI(title="ConfigVPN API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inject storage instance into every router via app.state
app.state.storage = storage

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(plans.router, prefix="/api/plans", tags=["plans"])
app.include_router(providers.router, prefix="/api/providers", tags=["providers"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(referrals.router, prefix="/api/referrals", tags=["referrals"])

app.include_router(admin_users.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_plans.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_payments.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_providers.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_settings.router, prefix="/api/admin", tags=["admin"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# SPA catch-all: serve static assets if they exist, otherwise return index.html
# This must come AFTER all API routes so API endpoints are matched first.
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
_assets_dir = _frontend_dist / "assets"

if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if _frontend_dist.exists():
        file_path = _frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        index = _frontend_dist / "index.html"
        if index.exists():
            return FileResponse(str(index))
    return {"detail": "Frontend not built"}
