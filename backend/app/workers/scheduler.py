"""Periodic collection.

Wakes on a fixed tick, asks which configurations are due, and runs them one at
a time. Sequential by design: collection opens SSH and SNMP sessions against
production network equipment, and a burst of parallel sessions is exactly the
kind of load that gets a monitoring tool banned from a network.

Each connector runs in a worker thread so blocking device I/O never stalls the
API's event loop.
"""
from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class CollectionScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self.running = False
        self.ticks = 0
        self.runs_started = 0

    async def start(self) -> None:
        if self.running or not settings.SCHEDULER_ENABLED:
            return
        self._task = asyncio.create_task(self._loop())
        self.running = True
        logger.info(
            "Collection scheduler started; tick every %s seconds", settings.SCHEDULER_TICK_SECONDS
        )

    async def _loop(self) -> None:
        # Let the API finish starting before touching the database.
        await asyncio.sleep(10)
        while True:
            try:
                await asyncio.sleep(settings.SCHEDULER_TICK_SECONDS)
                self.ticks += 1
                await asyncio.to_thread(self._run_due)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - the loop must survive anything
                logger.error("Collection scheduler tick failed: %s", exc)

    def _run_due(self) -> None:
        from app.services.collection import due_configs, execute_run

        db = SessionLocal()
        try:
            pending = due_configs(db)
            if not pending:
                return
            logger.info("Collection scheduler found %s due connector(s)", len(pending))
            for config in pending:
                try:
                    self.runs_started += 1
                    execute_run(db, config, trigger="schedule")
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Scheduled connector %s failed: %s", config.name, exc
                    )
                    db.rollback()
        finally:
            db.close()

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.running = False

    def stats(self) -> dict[str, int | bool]:
        return {
            "running": self.running,
            "ticks": self.ticks,
            "runs_started": self.runs_started,
        }


collection_scheduler = CollectionScheduler()
