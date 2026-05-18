"""User subscription endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from dependencies import get_current_user

router = APIRouter()


@router.get("")
async def get_subscriptions(
    request: Request,
    user_id: Annotated[int, Depends(get_current_user)],
):
    storage = request.app.state.storage
    subs = await storage.get_user_subscriptions(user_id, active_only=False)
    return [s.__dict__ for s in subs]
