"""Public subscription plans endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("")
async def list_plans(request: Request):
    storage = request.app.state.storage
    plans = await storage.get_subscription_plans(active_only=True)
    return [p.__dict__ for p in plans]
