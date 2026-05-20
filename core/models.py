"""Data models for the VPN bot system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    telegram_id: int
    phone: str
    username: str | None
    full_name: str
    referral_code: str
    referred_by: str | None
    bonus_gb: float
    is_blocked: bool
    created_at: str  # ISO datetime


@dataclass
class SubscriptionPlan:
    id: str
    name: str
    type: str               # "whitelist" or "regular"
    price: float
    duration_days: int
    traffic_gb: float
    description: str
    is_active: bool
    max_connections: int = 1          # simultaneous devices
    monthly_traffic_gb: float = 0.0  # 0 = unlimited
    sort_order: int = 0
    badge: str | None = None          # "popular", "profitable", or None


@dataclass
class Provider:
    id: str
    name: str
    location: str
    server_ip: str
    is_active: bool
    supports_whitelist: bool
    is_russian: bool = False


@dataclass
class Preset:
    id: str
    provider_id: str
    ram_gb: int
    cpu_count: int
    price: float
    is_active: bool


@dataclass
class Subscription:
    id: str
    user_id: int
    type: str               # "whitelist" or "regular"
    kind: str               # "ready" or "custom"
    plan_id: str | None
    provider_ids: list[str]
    preset_id: str | None
    traffic_gb: float
    used_gb: float
    expires_at: str | None  # ISO datetime
    is_active: bool
    subscription_url: str | None


@dataclass
class Requisite:
    id: str
    type: str               # "card" or "phone"
    value: str
    holder_name: str
    is_active: bool


@dataclass
class Payment:
    id: str
    user_id: int
    amount: float
    type: str               # "subscription" or "custom_vpn"
    product_ref: str
    product_details: dict
    requisite_id: str
    last4: str | None
    status: str             # "pending", "confirmed", "rejected"
    created_at: str
    reviewed_at: str | None
    reviewed_by: int | None


@dataclass
class Referral:
    id: str
    referrer_id: int
    referred_id: int
    bonus_applied: bool
    created_at: str


@dataclass
class Settings:
    admin_ids: list[int]
    bot_username: str
    referral_bonus_gb: float
    faq_text: str
    notifications: dict
