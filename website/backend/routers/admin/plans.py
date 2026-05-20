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
    sort_order: int = 0
    badge: str | None = None


class PlanPatch(BaseModel):
    name: str | None = None
    price: float | None = None
    description: str | None = None
    is_active: bool | None = None
    max_connections: int | None = None
    monthly_traffic_gb: float | None = None
    sort_order: int | None = None
    badge: str | None = None


class ReorderItem(BaseModel):
    id: str
    sort_order: int


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
        sort_order=body.sort_order,
        badge=body.badge,
    )
    await storage.save_subscription_plan(plan)
    return plan.__dict__


# Must be defined before PUT /{plan_id} to avoid route conflict
@router.put("/plans/reorder")
async def reorder_plans(
    body: list[ReorderItem],
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    for item in body:
        plan = await storage.get_subscription_plan(item.id)
        if plan:
            plan.sort_order = item.sort_order
            await storage.save_subscription_plan(plan)
    return {"status": "ok"}


@router.patch("/plans/{plan_id}")
async def patch_plan(
    plan_id: str,
    body: PlanPatch,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    plan = await storage.get_subscription_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    if body.name is not None: plan.name = body.name
    if body.price is not None: plan.price = body.price
    if body.description is not None: plan.description = body.description
    if body.is_active is not None: plan.is_active = body.is_active
    if body.max_connections is not None: plan.max_connections = body.max_connections
    if body.monthly_traffic_gb is not None: plan.monthly_traffic_gb = body.monthly_traffic_gb
    if body.sort_order is not None: plan.sort_order = body.sort_order
    # badge can be explicitly set to None to clear it
    if "badge" in body.model_fields_set: plan.badge = body.badge
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
    plan.sort_order = body.sort_order
    plan.badge = body.badge

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
