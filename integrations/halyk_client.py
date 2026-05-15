"""Halyk ePay 2.0 — Invoice Link API.

Only the surface we need for one-off skin purchases:
- create_invoice(...) → returns invoice_url to redirect the user to
- get_status(invoice_id) → polled by the reconcile job for stale pending payments
- refund(transaction_id, amount?) → manual or auto-refund on duplicate purchase

P2P payout flows (sending money out to recipient cards) live in the original
cafe project and are intentionally not ported here — we only collect money.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal

import httpx

from config import settings


@dataclass(frozen=True)
class HalykConfig:
    client_id: str
    client_secret: str
    shop_id: str       # for invoice creation
    terminal_id: str   # for refund / status


class HalykURLs:
    def __init__(self):
        self.oauth = settings.halyk_oauth_url  # e.g. https://test-epay-oauth.epayment.kz/oauth2/token
        self.api = settings.halyk_api_url      # e.g. https://test-epay-api.epayment.kz


class HalykClient:
    INVOICE_SCOPE = "payment"
    OPS_SCOPE = "webapi usermanagement email_send verification statement statistics payment"

    def __init__(self, config: HalykConfig):
        self.config = config
        self.urls = HalykURLs()
        self._ops_token: str | None = None
        self._ops_token_expires_at: float = 0.0

    # ---------- Invoice link ----------

    async def create_invoice(
        self,
        *,
        invoice_id: str,
        amount: Decimal,
        description: str,
        account_id: str,
        email: str,
        phone: str | None,
        post_link: str,
        back_link: str,
        failure_back_link: str | None = None,
        expire_period: str = "1d",
        language: str = "rus",
    ) -> dict:
        token = await self._get_invoice_token()
        payload = {
            "shop_id": self.config.shop_id,
            "account_id": account_id,
            "invoice_id": invoice_id,
            "amount": float(amount),
            "currency": "KZT",
            "language": language,
            "description": description[:125],
            "expire_period": expire_period,
            "recipient_contact": email,
            "post_link": post_link,
            "back_link": back_link,
            "failure_back_link": failure_back_link or back_link,
        }
        if phone:
            payload["recipient_contact_sms"] = phone

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.urls.api}/invoice",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def _get_invoice_token(self) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.urls.oauth,
                data={
                    "grant_type": "client_credentials",
                    "scope": self.INVOICE_SCOPE,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
            )
            response.raise_for_status()
            return response.json()["access_token"]

    # ---------- Status / refund ----------

    async def get_status(self, invoice_id: str) -> dict:
        token = await self._get_ops_token()
        url = f"{self.urls.api}/check-status/payment/transaction/{invoice_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            return response.json()

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal | None = None,
    ) -> bool:
        """amount=None → full refund; amount=X → partial (Halyk minimum is 10 KZT)."""
        token = await self._get_ops_token()
        url = f"{self.urls.api}/operation/{transaction_id}/refund"
        params = {"amount": str(amount)} if amount is not None else {}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.status_code == 200

    async def _get_ops_token(self) -> str:
        now = time.monotonic()
        if self._ops_token and now < self._ops_token_expires_at:
            return self._ops_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.urls.oauth,
                data={
                    "grant_type": "client_credentials",
                    "scope": self.OPS_SCOPE,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "terminal": self.config.terminal_id,
                },
            )
        response.raise_for_status()
        payload = response.json()
        self._ops_token = payload["access_token"]
        # Refresh 5 min before expiry, never less than 60s.
        self._ops_token_expires_at = now + max(int(payload.get("expires_in", 7200)) - 300, 60)
        return self._ops_token


def build_halyk_client() -> HalykClient:
    return HalykClient(HalykConfig(
        client_id=settings.halyk_client_id,
        client_secret=settings.halyk_client_secret.get_secret_value(),
        shop_id=settings.halyk_shop_id,
        terminal_id=settings.halyk_terminal_id,
    ))


_singleton: HalykClient | None = None


def get_halyk_client() -> HalykClient:
    """Process-wide HalykClient (caches OAuth tokens between requests)."""
    global _singleton
    if _singleton is None:
        _singleton = build_halyk_client()
    return _singleton


def is_halyk_configured() -> bool:
    return bool(settings.halyk_client_id and settings.halyk_shop_id)
