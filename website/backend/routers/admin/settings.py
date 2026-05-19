"""Admin settings endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.models import Requisite
from core.storage import JSONStorage
from dependencies import get_current_admin, hash_password

router = APIRouter()


class SettingsBody(BaseModel):
    faq_text: str | None = None
    referral_bonus_gb: float | None = None
    bot_username: str | None = None


class AdminCredBody(BaseModel):
    username: str
    password: str


class RequisiteBody(BaseModel):
    type: str  # "card" or "phone"
    value: str
    holder_name: str
    is_active: bool = True


@router.get("/settings")
async def get_settings(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    data = await storage._read("settings.json", {})
    # Don't expose password hashes
    creds = data.get("admin_credentials", [])
    safe_creds = [{"username": c["username"]} for c in creds]
    return {
        "admin_ids": data.get("admin_ids", []),
        "bot_username": data.get("bot_username", ""),
        "referral_bonus_gb": data.get("referral_bonus_gb", 30.0),
        "faq_text": data.get("faq_text", ""),
        "notifications": data.get("notifications", {}),
        "admin_credentials": safe_creds,
    }


@router.patch("/settings")
async def update_settings(
    body: SettingsBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    data = await storage._read("settings.json", {})

    if body.faq_text is not None:
        data["faq_text"] = body.faq_text
    if body.referral_bonus_gb is not None:
        data["referral_bonus_gb"] = body.referral_bonus_gb
    if body.bot_username is not None:
        data["bot_username"] = body.bot_username

    await storage._write("settings.json", data)
    return {"status": "ok"}


@router.post("/settings/admin-credentials")
async def add_admin_credential(
    body: AdminCredBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    data = await storage._read("settings.json", {})
    creds = data.get("admin_credentials", [])

    # Check if username already exists
    for c in creds:
        if c["username"] == body.username:
            raise HTTPException(status_code=400, detail="Администратор уже существует")

    creds.append({"username": body.username, "password_hash": hash_password(body.password)})
    data["admin_credentials"] = creds
    await storage._write("settings.json", data)
    return {"status": "ok", "username": body.username}


@router.delete("/settings/admin-credentials/{username}")
async def delete_admin_credential(
    username: str,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    if admin.get("username") == username:
        raise HTTPException(status_code=400, detail="Нельзя удалить свою учётную запись")

    storage: JSONStorage = request.app.state.storage
    data = await storage._read("settings.json", {})
    creds = data.get("admin_credentials", [])
    data["admin_credentials"] = [c for c in creds if c["username"] != username]
    await storage._write("settings.json", data)
    return {"status": "deleted"}


@router.post("/requisites")
async def create_requisite(
    body: RequisiteBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    req = Requisite(
        id=storage.new_id(),
        type=body.type,
        value=body.value,
        holder_name=body.holder_name,
        is_active=body.is_active,
    )
    await storage.save_requisite(req)
    return req.__dict__


@router.put("/requisites/{req_id}")
async def update_requisite(
    req_id: str,
    body: RequisiteBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    req = await storage.get_requisite(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Реквизит не найден")

    req.type = body.type
    req.value = body.value
    req.holder_name = body.holder_name
    req.is_active = body.is_active

    await storage.save_requisite(req)
    return req.__dict__


@router.delete("/requisites/{req_id}")
async def delete_requisite(
    req_id: str,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    await storage.delete_requisite(req_id)
    return {"status": "deleted"}
