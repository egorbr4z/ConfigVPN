"""
Storage layer with abstract base and JSON file implementation.

The interface is designed so that it can be swapped out for an API or
database backend without touching any handler code.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import aiofiles

from core.models import (
    User,
    SubscriptionPlan,
    Provider,
    Preset,
    Subscription,
    Requisite,
    Payment,
    Referral,
    Settings,
)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class BaseStorage(ABC):
    # Users
    @abstractmethod
    async def get_user(self, telegram_id: int) -> User | None: ...

    @abstractmethod
    async def save_user(self, user: User) -> None: ...

    @abstractmethod
    async def get_all_users(self) -> list[User]: ...

    # Subscription plans
    @abstractmethod
    async def get_subscription_plans(self, active_only: bool = True) -> list[SubscriptionPlan]: ...

    @abstractmethod
    async def get_subscription_plan(self, plan_id: str) -> SubscriptionPlan | None: ...

    @abstractmethod
    async def save_subscription_plan(self, plan: SubscriptionPlan) -> None: ...

    @abstractmethod
    async def delete_subscription_plan(self, plan_id: str) -> None: ...

    # Providers
    @abstractmethod
    async def get_providers(self, active_only: bool = True) -> list[Provider]: ...

    @abstractmethod
    async def get_provider(self, provider_id: str) -> Provider | None: ...

    @abstractmethod
    async def save_provider(self, provider: Provider) -> None: ...

    @abstractmethod
    async def delete_provider(self, provider_id: str) -> None: ...

    # Presets
    @abstractmethod
    async def get_presets(self, provider_id: str | None = None, active_only: bool = True) -> list[Preset]: ...

    @abstractmethod
    async def get_preset(self, preset_id: str) -> Preset | None: ...

    @abstractmethod
    async def save_preset(self, preset: Preset) -> None: ...

    @abstractmethod
    async def delete_preset(self, preset_id: str) -> None: ...

    # Subscriptions
    @abstractmethod
    async def get_user_subscriptions(self, user_id: int, active_only: bool = False) -> list[Subscription]: ...

    @abstractmethod
    async def get_subscription(self, subscription_id: str) -> Subscription | None: ...

    @abstractmethod
    async def save_subscription(self, subscription: Subscription) -> None: ...

    @abstractmethod
    async def get_all_subscriptions(self, active_only: bool = False) -> list[Subscription]: ...

    # Requisites
    @abstractmethod
    async def get_requisites(self, active_only: bool = True) -> list[Requisite]: ...

    @abstractmethod
    async def get_requisite(self, requisite_id: str) -> Requisite | None: ...

    @abstractmethod
    async def save_requisite(self, requisite: Requisite) -> None: ...

    @abstractmethod
    async def delete_requisite(self, requisite_id: str) -> None: ...

    # Payments
    @abstractmethod
    async def get_payments(self, status: str | None = None) -> list[Payment]: ...

    @abstractmethod
    async def get_payment(self, payment_id: str) -> Payment | None: ...

    @abstractmethod
    async def save_payment(self, payment: Payment) -> None: ...

    @abstractmethod
    async def get_user_payments(self, user_id: int) -> list[Payment]: ...

    # Referrals
    @abstractmethod
    async def get_referral_by_code(self, code: str) -> User | None: ...

    @abstractmethod
    async def save_referral(self, referral: Referral) -> None: ...

    @abstractmethod
    async def get_referrals_by_referrer(self, referrer_id: int) -> list[Referral]: ...

    @abstractmethod
    async def get_referral_by_referred(self, referred_id: int) -> Referral | None: ...

    # Settings
    @abstractmethod
    async def get_settings(self) -> Settings: ...

    @abstractmethod
    async def save_settings(self, settings: Settings) -> None: ...

    # Utility
    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# JSON implementation
# ---------------------------------------------------------------------------

class JSONStorage(BaseStorage):
    """Stores all data as JSON files under ``data_dir``."""

    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        # Per-file async locks to prevent concurrent writes
        self._locks: dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lock_for(self, filename: str) -> asyncio.Lock:
        if filename not in self._locks:
            self._locks[filename] = asyncio.Lock()
        return self._locks[filename]

    def _path(self, filename: str) -> Path:
        return self._dir / filename

    async def _read(self, filename: str, default: Any = None) -> Any:
        path = self._path(filename)
        if not path.exists():
            return default if default is not None else {}

        def _do_read():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        return await asyncio.to_thread(_do_read)

    async def _write(self, filename: str, data: Any) -> None:
        path = self._path(filename)
        lock = self._lock_for(filename)

        def _do_write():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        async with lock:
            await asyncio.to_thread(_do_write)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def get_user(self, telegram_id: int) -> User | None:
        data = await self._read("users.json", {})
        raw = data.get(str(telegram_id))
        if raw is None:
            return None
        return User(**raw)

    async def save_user(self, user: User) -> None:
        data = await self._read("users.json", {})
        data[str(user.telegram_id)] = user.__dict__
        await self._write("users.json", data)

    async def get_all_users(self) -> list[User]:
        data = await self._read("users.json", {})
        return [User(**v) for v in data.values()]

    # ------------------------------------------------------------------
    # Subscription plans
    # ------------------------------------------------------------------

    @staticmethod
    def _plan_from_raw(raw: dict) -> SubscriptionPlan:
        raw = raw.copy()
        valid = set(SubscriptionPlan.__dataclass_fields__.keys())
        raw = {k: v for k, v in raw.items() if k in valid}
        return SubscriptionPlan(**raw)

    async def get_subscription_plans(self, active_only: bool = True) -> list[SubscriptionPlan]:
        data = await self._read("subscription_plans.json", {})
        plans = [self._plan_from_raw(v) for v in data.values()]
        if active_only:
            plans = [p for p in plans if p.is_active]
        return plans

    async def get_subscription_plan(self, plan_id: str) -> SubscriptionPlan | None:
        data = await self._read("subscription_plans.json", {})
        raw = data.get(plan_id)
        return self._plan_from_raw(raw) if raw else None

    async def save_subscription_plan(self, plan: SubscriptionPlan) -> None:
        data = await self._read("subscription_plans.json", {})
        data[plan.id] = plan.__dict__
        await self._write("subscription_plans.json", data)

    async def delete_subscription_plan(self, plan_id: str) -> None:
        data = await self._read("subscription_plans.json", {})
        data.pop(plan_id, None)
        await self._write("subscription_plans.json", data)

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    async def get_providers(self, active_only: bool = True) -> list[Provider]:
        data = await self._read("providers.json", {})
        providers = [Provider(**v) for v in data.values()]
        if active_only:
            providers = [p for p in providers if p.is_active]
        return providers

    async def get_provider(self, provider_id: str) -> Provider | None:
        data = await self._read("providers.json", {})
        raw = data.get(provider_id)
        return Provider(**raw) if raw else None

    async def save_provider(self, provider: Provider) -> None:
        data = await self._read("providers.json", {})
        data[provider.id] = provider.__dict__
        await self._write("providers.json", data)

    async def delete_provider(self, provider_id: str) -> None:
        data = await self._read("providers.json", {})
        data.pop(provider_id, None)
        await self._write("providers.json", data)

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    async def get_presets(self, provider_id: str | None = None, active_only: bool = True) -> list[Preset]:
        data = await self._read("presets.json", {})
        presets = [Preset(**v) for v in data.values()]
        if active_only:
            presets = [p for p in presets if p.is_active]
        if provider_id is not None:
            presets = [p for p in presets if p.provider_id == provider_id]
        return presets

    async def get_preset(self, preset_id: str) -> Preset | None:
        data = await self._read("presets.json", {})
        raw = data.get(preset_id)
        return Preset(**raw) if raw else None

    async def save_preset(self, preset: Preset) -> None:
        data = await self._read("presets.json", {})
        data[preset.id] = preset.__dict__
        await self._write("presets.json", data)

    async def delete_preset(self, preset_id: str) -> None:
        data = await self._read("presets.json", {})
        data.pop(preset_id, None)
        await self._write("presets.json", data)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def _read_subscriptions(self) -> dict:
        return await self._read("subscriptions.json", {})

    def _sub_from_raw(self, raw: dict) -> Subscription:
        raw = raw.copy()
        # Migrate old v2ray_config field to subscription_url
        if "v2ray_config" in raw:
            old = raw.pop("v2ray_config")
            if "subscription_url" not in raw:
                raw["subscription_url"] = None
        # Remove any unknown keys to avoid TypeError
        valid = set(Subscription.__dataclass_fields__.keys())
        raw = {k: v for k, v in raw.items() if k in valid}
        return Subscription(**raw)

    async def get_user_subscriptions(self, user_id: int, active_only: bool = False) -> list[Subscription]:
        data = await self._read_subscriptions()
        subs = [self._sub_from_raw(v) for v in data.values() if v["user_id"] == user_id]
        if active_only:
            subs = [s for s in subs if s.is_active]
        return subs

    async def get_subscription(self, subscription_id: str) -> Subscription | None:
        data = await self._read_subscriptions()
        raw = data.get(subscription_id)
        return self._sub_from_raw(raw) if raw else None

    async def save_subscription(self, subscription: Subscription) -> None:
        data = await self._read_subscriptions()
        raw = subscription.__dict__.copy()
        # provider_ids is already a list, no special treatment needed
        data[subscription.id] = raw
        await self._write("subscriptions.json", data)

    async def get_all_subscriptions(self, active_only: bool = False) -> list[Subscription]:
        data = await self._read_subscriptions()
        subs = [self._sub_from_raw(v) for v in data.values()]
        if active_only:
            subs = [s for s in subs if s.is_active]
        return subs

    # ------------------------------------------------------------------
    # Requisites
    # ------------------------------------------------------------------

    async def get_requisites(self, active_only: bool = True) -> list[Requisite]:
        data = await self._read("requisites.json", {})
        reqs = [Requisite(**v) for v in data.values()]
        if active_only:
            reqs = [r for r in reqs if r.is_active]
        return reqs

    async def get_requisite(self, requisite_id: str) -> Requisite | None:
        data = await self._read("requisites.json", {})
        raw = data.get(requisite_id)
        return Requisite(**raw) if raw else None

    async def save_requisite(self, requisite: Requisite) -> None:
        data = await self._read("requisites.json", {})
        data[requisite.id] = requisite.__dict__
        await self._write("requisites.json", data)

    async def delete_requisite(self, requisite_id: str) -> None:
        data = await self._read("requisites.json", {})
        data.pop(requisite_id, None)
        await self._write("requisites.json", data)

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    async def get_payments(self, status: str | None = None) -> list[Payment]:
        data = await self._read("payments.json", {})
        payments = [Payment(**v) for v in data.values()]
        if status is not None:
            payments = [p for p in payments if p.status == status]
        return payments

    async def get_payment(self, payment_id: str) -> Payment | None:
        data = await self._read("payments.json", {})
        raw = data.get(payment_id)
        return Payment(**raw) if raw else None

    async def save_payment(self, payment: Payment) -> None:
        data = await self._read("payments.json", {})
        data[payment.id] = payment.__dict__
        await self._write("payments.json", data)

    async def get_user_payments(self, user_id: int) -> list[Payment]:
        data = await self._read("payments.json", {})
        return [Payment(**v) for v in data.values() if v["user_id"] == user_id]

    # ------------------------------------------------------------------
    # Referrals
    # ------------------------------------------------------------------

    async def get_referral_by_code(self, code: str) -> User | None:
        """Return the user who owns this referral code."""
        data = await self._read("users.json", {})
        for raw in data.values():
            if raw.get("referral_code") == code:
                return User(**raw)
        return None

    async def save_referral(self, referral: Referral) -> None:
        data = await self._read("referrals.json", {})
        data[referral.id] = referral.__dict__
        await self._write("referrals.json", data)

    async def get_referrals_by_referrer(self, referrer_id: int) -> list[Referral]:
        data = await self._read("referrals.json", {})
        return [Referral(**v) for v in data.values() if v["referrer_id"] == referrer_id]

    async def get_referral_by_referred(self, referred_id: int) -> Referral | None:
        data = await self._read("referrals.json", {})
        for raw in data.values():
            if raw["referred_id"] == referred_id:
                return Referral(**raw)
        return None

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    async def get_settings(self) -> Settings:
        data = await self._read("settings.json", {})
        return Settings(
            admin_ids=data.get("admin_ids", []),
            bot_username=data.get("bot_username", ""),
            referral_bonus_gb=data.get("referral_bonus_gb", 30.0),
            faq_text=data.get("faq_text", "FAQ не настроен."),
            notifications=data.get("notifications", {"notify_admins_on_payment": True}),
        )

    async def save_settings(self, settings: Settings) -> None:
        await self._write("settings.json", settings.__dict__)
