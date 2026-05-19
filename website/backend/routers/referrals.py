"""Referral endpoints for authenticated users."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from dependencies import get_current_user

router = APIRouter()


@router.get("/stats")
async def referral_stats(
    request: Request,
    user_id: Annotated[int, Depends(get_current_user)],
):
    storage = request.app.state.storage
    user = await storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    referrals = await storage.get_referrals_by_referrer(user_id)
    return {
        "referral_code": user.referral_code,
        "invited_count": len(referrals),
        "bonus_gb": user.bonus_gb,
    }


@router.get("/link")
async def referral_link(
    request: Request,
    user_id: Annotated[int, Depends(get_current_user)],
):
    storage = request.app.state.storage
    user = await storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    settings_data = await storage._read("settings.json", {})
    bot_username = settings_data.get("bot_username", "")
    link = f"https://t.me/{bot_username}?start={user.referral_code}" if bot_username else None
    web_link = f"{request.base_url}register?ref={user.referral_code}"
    return {
        "referral_code": user.referral_code,
        "telegram_link": link,
        "web_link": web_link,
    }
