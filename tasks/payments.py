"""Celery tasks for payments — reconciliation of pending invoices with Halyk."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import settings
from integrations.halyk_client import build_halyk_client
from services.payment_service import PaymentService
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="checkers.tasks.payments.reconcile_pending_payments")
def reconcile_pending_payments():
    """Pick up pending payments that never got a postlink and sync with Halyk. Runs every 10 min."""
    return asyncio.run(_run())


async def _run():
    engine = create_async_engine(settings.database_url)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    halyk = build_halyk_client()

    async with session_maker() as session:
        service = PaymentService(session, halyk)
        count = await service.reconcile_pending(max_age_minutes=10)
        logger.info("Reconciled %d payments", count)

    await engine.dispose()
    return {"reconciled": count}
