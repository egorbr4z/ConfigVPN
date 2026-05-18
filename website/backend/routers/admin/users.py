"""Admin user management endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from dependencies import get_current_admin

router = APIRouter()


class PatchUserBody(BaseModel):
    is_blocked: bool | None = None
    bonus_gb: float | None = None
    full_name: str | None = None


@router.get("/stats")
async def get_stats(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage = request.app.state.storage
    users = await storage.get_all_users()
    payments = await storage.get_payments()
    subscriptions = await storage.get_all_subscriptions(active_only=True)
    pending = [p for p in payments if p.status == "pending"]
    return {
        "total_users": len(users),
        "pending_payments": len(pending),
        "active_subscriptions": len(subscriptions),
        "total_payments": len(payments),
    }


@router.get("/users")
async def list_users(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
    search: str = "",
    page: int = 1,
    per_page: int = 20,
):
    storage = request.app.state.storage
    users = await storage.get_all_users()

    if search:
        q = search.lower()
        users = [
            u for u in users
            if q in (u.phone or "").lower()
            or q in (u.full_name or "").lower()
            or q in (u.username or "").lower()
        ]

    users.sort(key=lambda u: u.created_at, reverse=True)
    total = len(users)
    start = (page - 1) * per_page
    page_users = users[start: start + per_page]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": [u.__dict__ for u in page_users],
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage = request.app.state.storage
    user = await storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    subscriptions = await storage.get_user_subscriptions(user_id)
    payments = await storage.get_user_payments(user_id)

    return {
        **user.__dict__,
        "subscriptions": [s.__dict__ for s in subscriptions],
        "payments": [p.__dict__ for p in payments],
    }


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: int,
    body: PatchUserBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage = request.app.state.storage
    user = await storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if body.is_blocked is not None:
        user.is_blocked = body.is_blocked
    if body.bonus_gb is not None:
        user.bonus_gb = body.bonus_gb
    if body.full_name is not None:
        user.full_name = body.full_name

    await storage.save_user(user)
    return user.__dict__
