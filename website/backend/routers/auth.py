"""Authentication endpoints."""

from __future__ import annotations

import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from core.models import User
from dependencies import create_access_token, hash_password, verify_password

router = APIRouter()


def _storage(request: Request):
    return request.app.state.storage


def _gen_referral_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _web_user_id(phone: str) -> int:
    """Generate a stable numeric ID from a phone number for web-only users."""
    return (abs(hash(phone)) % 2_147_483_647) + 1


class RegisterBody(BaseModel):
    phone: str
    password: str
    full_name: str
    referral_code: str | None = None


class LoginBody(BaseModel):
    phone: str
    password: str


class AdminLoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(body: RegisterBody, request: Request):
    storage = _storage(request)

    # Check if phone already used
    all_users = await storage.get_all_users()
    for u in all_users:
        if u.phone == body.phone:
            raise HTTPException(status_code=400, detail="Телефон уже зарегистрирован")

    # Handle referral
    referrer = None
    if body.referral_code:
        referrer = await storage.get_referral_by_code(body.referral_code)

    user_id = _web_user_id(body.phone)
    referral_code = _gen_referral_code()
    # Ensure uniqueness
    existing_codes = {u.referral_code for u in all_users}
    while referral_code in existing_codes:
        referral_code = _gen_referral_code()

    user = User(
        telegram_id=user_id,
        phone=body.phone,
        username=None,
        full_name=body.full_name,
        referral_code=referral_code,
        referred_by=referrer.referral_code if referrer else None,
        bonus_gb=0.0,
        is_blocked=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await storage.save_user(user)

    # Store password hash separately
    pw_data = await storage._read("user_passwords.json", {})
    pw_data[body.phone] = hash_password(body.password)
    await storage._write("user_passwords.json", pw_data)

    token = create_access_token({"user_id": user_id, "phone": body.phone, "role": "user"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "phone": user.phone,
            "full_name": user.full_name,
            "referral_code": user.referral_code,
            "bonus_gb": user.bonus_gb,
        },
    }


@router.post("/login")
async def login(body: LoginBody, request: Request):
    storage = _storage(request)

    pw_data = await storage._read("user_passwords.json", {})
    pw_hash = pw_data.get(body.phone)
    if not pw_hash or not verify_password(body.password, pw_hash):
        raise HTTPException(status_code=401, detail="Неверный телефон или пароль")

    all_users = await storage.get_all_users()
    user = next((u for u in all_users if u.phone == body.phone), None)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")

    token = create_access_token({"user_id": user.telegram_id, "phone": user.phone, "role": "user"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.telegram_id,
            "phone": user.phone,
            "full_name": user.full_name,
            "referral_code": user.referral_code,
            "bonus_gb": user.bonus_gb,
        },
    }


@router.post("/admin-login")
async def admin_login(body: AdminLoginBody, request: Request):
    storage = _storage(request)

    settings_data = await storage._read("settings.json", {})
    credentials_list = settings_data.get("admin_credentials", [])

    matched = False
    for cred in credentials_list:
        if cred.get("username") == body.username:
            if verify_password(body.password, cred.get("password_hash", "")):
                matched = True
                break

    if not matched:
        raise HTTPException(status_code=401, detail="Неверные учётные данные")

    token = create_access_token({"username": body.username, "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}
