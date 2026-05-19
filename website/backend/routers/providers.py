"""Public providers endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("")
async def list_providers(request: Request):
    storage = request.app.state.storage
    providers = await storage.get_providers(active_only=True)
    return [p.__dict__ for p in providers]


@router.get("/presets")
async def list_presets(request: Request, provider_id: str | None = None):
    storage = request.app.state.storage
    presets = await storage.get_presets(provider_id=provider_id, active_only=True)
    return [p.__dict__ for p in presets]
