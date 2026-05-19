"""Admin provider and preset management endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.models import Provider, Preset
from core.storage import JSONStorage
from dependencies import get_current_admin

router = APIRouter()


class ProviderBody(BaseModel):
    name: str
    location: str
    server_ip: str
    is_active: bool = True
    supports_whitelist: bool = False
    is_russian: bool = False


class ProviderPatch(BaseModel):
    name: str | None = None
    location: str | None = None
    server_ip: str | None = None
    is_active: bool | None = None
    supports_whitelist: bool | None = None
    is_russian: bool | None = None


class PresetBody(BaseModel):
    provider_id: str
    ram_gb: int
    cpu_count: int
    price: float
    is_active: bool = True


@router.get("/providers")
async def list_providers(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    providers = await storage.get_providers(active_only=False)
    return [p.__dict__ for p in providers]


@router.post("/providers")
async def create_provider(
    body: ProviderBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    provider = Provider(
        id=storage.new_id(),
        name=body.name,
        location=body.location,
        server_ip=body.server_ip,
        is_active=body.is_active,
        supports_whitelist=body.supports_whitelist,
        is_russian=body.is_russian,
    )
    await storage.save_provider(provider)
    return provider.__dict__


@router.patch("/providers/{provider_id}")
async def patch_provider(
    provider_id: str,
    body: ProviderPatch,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    provider = await storage.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Провайдер не найден")
    if body.name is not None: provider.name = body.name
    if body.location is not None: provider.location = body.location
    if body.server_ip is not None: provider.server_ip = body.server_ip
    if body.is_active is not None: provider.is_active = body.is_active
    if body.supports_whitelist is not None: provider.supports_whitelist = body.supports_whitelist
    if body.is_russian is not None: provider.is_russian = body.is_russian
    await storage.save_provider(provider)
    return provider.__dict__


@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    body: ProviderBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    provider = await storage.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Провайдер не найден")

    provider.name = body.name
    provider.location = body.location
    provider.server_ip = body.server_ip
    provider.is_active = body.is_active
    provider.supports_whitelist = body.supports_whitelist
    provider.is_russian = body.is_russian

    await storage.save_provider(provider)
    return provider.__dict__


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: str,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    await storage.delete_provider(provider_id)
    return {"status": "deleted"}


@router.post("/presets")
async def create_preset(
    body: PresetBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    preset = Preset(
        id=storage.new_id(),
        provider_id=body.provider_id,
        ram_gb=body.ram_gb,
        cpu_count=body.cpu_count,
        price=body.price,
        is_active=body.is_active,
    )
    await storage.save_preset(preset)
    return preset.__dict__


@router.put("/presets/{preset_id}")
async def update_preset(
    preset_id: str,
    body: PresetBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    preset = await storage.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Пресет не найден")

    preset.provider_id = body.provider_id
    preset.ram_gb = body.ram_gb
    preset.cpu_count = body.cpu_count
    preset.price = body.price
    preset.is_active = body.is_active

    await storage.save_preset(preset)
    return preset.__dict__


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: str,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    await storage.delete_preset(preset_id)
    return {"status": "deleted"}
