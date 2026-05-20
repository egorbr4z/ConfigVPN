"""Admin payment management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.models import Subscription
from core.storage import JSONStorage
from dependencies import get_current_admin

router = APIRouter()


class ConfirmPaymentBody(BaseModel):
    subscription_url: str


class RejectPaymentBody(BaseModel):
    reason: str = ""


@router.get("/payments")
async def list_payments(
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
    status: str | None = None,
    page: int = 1,
    per_page: int = 30,
):
    storage: JSONStorage = request.app.state.storage
    payments = await storage.get_payments(status=status)
    payments.sort(key=lambda p: p.created_at, reverse=True)

    total = len(payments)
    start = (page - 1) * per_page
    page_payments = payments[start: start + per_page]

    # Enrich with user info
    result = []
    for p in page_payments:
        user = await storage.get_user(p.user_id)
        item = p.__dict__.copy()
        item["user_phone"] = user.phone if user else "—"
        item["user_name"] = user.full_name if user else "—"
        result.append(item)

    return {"total": total, "page": page, "per_page": per_page, "items": result}


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    payment = await storage.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")

    user = await storage.get_user(payment.user_id)
    requisite = await storage.get_requisite(payment.requisite_id)

    result = payment.__dict__.copy()
    result["user_phone"] = user.phone if user else "—"
    result["user_name"] = user.full_name if user else "—"
    if requisite:
        result["requisite"] = requisite.__dict__
    return result


@router.post("/payments/{payment_id}/confirm")
async def confirm_payment(
    payment_id: str,
    body: ConfirmPaymentBody,
    request: Request,
    admin: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    payment = await storage.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Платёж уже обработан")

    now = datetime.now(timezone.utc).isoformat()
    payment.status = "confirmed"
    payment.reviewed_at = now
    await storage.save_payment(payment)

    # Create subscription
    details = payment.product_details
    sub_id = storage.new_id()

    if payment.type == "subscription":
        plan = await storage.get_subscription_plan(payment.product_ref)
        duration_days = details.get("duration_days", 30)
        from datetime import timedelta
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=duration_days)
        ).isoformat()
        sub = Subscription(
            id=sub_id,
            user_id=payment.user_id,
            type=details.get("type", "regular"),
            kind="ready",
            plan_id=payment.product_ref,
            provider_ids=[],
            preset_id=None,
            traffic_gb=details.get("traffic_gb", 0),
            used_gb=0.0,
            expires_at=expires_at,
            is_active=True,
            subscription_url=body.subscription_url,
        )
    else:
        sub = Subscription(
            id=sub_id,
            user_id=payment.user_id,
            type=details.get("vpn_type", "regular"),
            kind="custom",
            plan_id=None,
            provider_ids=details.get("provider_ids", []),
            preset_id=details.get("preset_id"),
            traffic_gb=0,
            used_gb=0.0,
            expires_at=None,
            is_active=True,
            subscription_url=body.subscription_url,
        )

    await storage.save_subscription(sub)

    # Apply referral bonus on first confirmed purchase
    user = await storage.get_user(payment.user_id)
    if user and user.referred_by:
        referral_record = await storage.get_referral_by_referred(payment.user_id)
        if referral_record and not referral_record.bonus_applied:
            # New flow: use Referral record with bonus_applied flag
            referrer = await storage.get_user(referral_record.referrer_id)
            if referrer:
                settings = await storage.get_settings()
                referrer.bonus_gb += settings.referral_bonus_gb
                await storage.save_user(referrer)
                referral_record.bonus_applied = True
                await storage.save_referral(referral_record)
        elif not referral_record:
            # Fallback for users registered before Referral records were introduced
            referrer = await storage.get_referral_by_code(user.referred_by)
            if referrer:
                user_payments = await storage.get_user_payments(payment.user_id)
                confirmed = [p for p in user_payments if p.status == "confirmed"]
                if len(confirmed) == 1:
                    settings = await storage.get_settings()
                    referrer.bonus_gb += settings.referral_bonus_gb
                    await storage.save_user(referrer)

    return {"status": "confirmed", "subscription_id": sub_id}


@router.post("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    body: RejectPaymentBody,
    request: Request,
    _: Annotated[dict, Depends(get_current_admin)],
):
    storage: JSONStorage = request.app.state.storage
    payment = await storage.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Платёж уже обработан")

    payment.status = "rejected"
    payment.reviewed_at = datetime.now(timezone.utc).isoformat()
    await storage.save_payment(payment)
    return {"status": "rejected"}
