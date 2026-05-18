"""Admin subscription plan CRUD endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.models import SubscriptionPlan
from core.storage import JSONStorage
from dependencies import get_current_admin

router = APIRouter()


class PlanBody(BaseModel):
    name: str
    type: str  # "whitelist" or "regular"
    price: float
    duration_days: int
    traffic_gb: float
    description: str
    is_active: bool = True
    max_connections: int = 1
    monthly_traffic_gb: float = 0.0


@router.get("/plans")
async def list_plans(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    plans = await storage.get_subscription_plans(active_only=False)
    return [p.__dict__ for p in plans]


@router.post("/plans")
async def create_plan(
    body: PlanBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    plan_id = storage.new_id()
    plan = SubscriptionPlan(
        id=plan_id,
        name=body.name,
        type=body.type,
        price=body.price,
        duration_days=body.duration_days,
        traffic_gb=body.traffic_gb,
        description=body.description,
        is_active=body.is_active,
        max_connections=body.max_connections,
        monthly_traffic_gb=body.monthly_traffic_gb,
    )
    await storage.save_subscription_plan(plan)
    return plan.__dict__


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    body: PlanBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    plan = await storage.get_subscription_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Тариф не найден")

    plan.name = body.name
    plan.type = body.type
    plan.price = body.price
    plan.duration_days = body.duration_days
    plan.traffic_gb = body.traffic_gb
    plan.description = body.description
    plan.is_active = body.is_active
    plan.max_connections = body.max_connections
    plan.monthly_traffic_gb = body.monthly_traffic_gb

    await storage.save_subscription_plan(plan)
    return plan.__dict__


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: str,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    await storage.delete_subscription_plan(plan_id)
    return {"status": "deleted"}


@router.get("/presets")
async def list_presets(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    presets = await storage.get_presets(active_only=False)
    return [p.__dict__ for p in presets]


@router.get("/requisites")
async def list_requisites(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    reqs = await storage.get_requisites(active_only=False)
    return [r.__dict__ for r in reqs]
