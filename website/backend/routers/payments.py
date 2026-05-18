"""Payment endpoints for authenticated users."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.models import Payment
from core.storage import JSONStorage
from dependencies import get_current_user

router = APIRouter()


class InitiatePaymentBody(BaseModel):
    type: str  # "subscription" or "custom_vpn"
    plan_id: str | None = None
    preset_id: str | None = None
    provider_ids: list[str] | None = None
    vpn_type: str | None = None  # "whitelist" or "regular"


class ConfirmLast4Body(BaseModel):
    last4: str


@router.post("/initiate")
async def initiate_payment(
    body: InitiatePaymentBody,
    request: Request,
    user_id: Annotated[int, Depends(get_current_user)],
):
    storage: JSONStorage = request.app.state.storage

    # Determine amount and product details
    amount = 0.0
    product_ref = ""
    product_details: dict = {}

    if body.type == "subscription":
        if not body.plan_id:
            raise HTTPException(status_code=400, detail="Требуется plan_id")
        plan = await storage.get_subscription_plan(body.plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Тариф не найден")
        amount = plan.price
        product_ref = plan.id
        product_details = {
            "plan_name": plan.name,
            "duration_days": plan.duration_days,
            "traffic_gb": plan.traffic_gb,
            "type": plan.type,
        }
    elif body.type == "custom_vpn":
        if not body.preset_id:
            raise HTTPException(status_code=400, detail="Требуется preset_id")
        preset = await storage.get_preset(body.preset_id)
        if not preset or not preset.is_active:
            raise HTTPException(status_code=404, detail="Пресет не найден")
        amount = preset.price
        product_ref = preset.id
        provider_ids = body.provider_ids or []
        product_details = {
            "preset_id": preset.id,
            "provider_ids": provider_ids,
            "vpn_type": body.vpn_type or "regular",
            "ram_gb": preset.ram_gb,
            "cpu_count": preset.cpu_count,
        }
    else:
        raise HTTPException(status_code=400, detail="Неверный тип платежа")

    # Pick a random active requisite
    requisites = await storage.get_requisites(active_only=True)
    if not requisites:
        raise HTTPException(status_code=503, detail="Реквизиты недоступны")
    requisite = random.choice(requisites)

    payment_id = storage.new_id()
    payment = Payment(
        id=payment_id,
        user_id=user_id,
        amount=amount,
        type=body.type,
        product_ref=product_ref,
        product_details=product_details,
        requisite_id=requisite.id,
        last4=None,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        reviewed_at=None,
        reviewed_by=None,
    )
    await storage.save_payment(payment)

    return {
        "payment_id": payment_id,
        "amount": amount,
        "requisite": {
            "id": requisite.id,
            "type": requisite.type,
            "value": requisite.value,
            "holder_name": requisite.holder_name,
        },
    }


@router.post("/{payment_id}/confirm-last4")
async def confirm_last4(
    payment_id: str,
    body: ConfirmLast4Body,
    request: Request,
    user_id: Annotated[int, Depends(get_current_user)],
):
    storage: JSONStorage = request.app.state.storage
    payment = await storage.get_payment(payment_id)
    if not payment or payment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Платёж уже обработан")

    payment.last4 = body.last4
    await storage.save_payment(payment)
    return {"status": "ok", "message": "Данные приняты, ожидайте подтверждения"}


@router.get("")
async def list_payments(
    request: Request,
    user_id: Annotated[int, Depends(get_current_user)],
):
    storage: JSONStorage = request.app.state.storage
    payments = await storage.get_user_payments(user_id)
    payments.sort(key=lambda p: p.created_at, reverse=True)
    return [p.__dict__ for p in payments]


@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    request: Request,
    user_id: Annotated[int, Depends(get_current_user)],
):
    storage: JSONStorage = request.app.state.storage
    payment = await storage.get_payment(payment_id)
    if not payment or payment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Платёж не найден")

    requisite = await storage.get_requisite(payment.requisite_id)
    result = payment.__dict__.copy()
    if requisite:
        result["requisite"] = requisite.__dict__
    return result
