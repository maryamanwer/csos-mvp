"""Single-flight scheduler for configured CSOS pull sources."""
from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.database import SessionLocal

log = logging.getLogger(__name__)


class CollectionScheduler:
    def __init__(self) -> None:
        self.running = False
        self.ticks = 0
        self.runs_started = 0
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.running or not settings.SCHEDULER_ENABLED:
            return
        self.running = True
        self._task = asyncio.create_task(self._serve(), name="csos-source-scheduler")

    async def _serve(self) -> None:
        while True:
            try:
                await asyncio.sleep(settings.SCHEDULER_TICK_SECONDS)
                self.ticks += 1
                await asyncio.to_thread(self._execute_due)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Source scheduler tick failed")

    def _execute_due(self) -> None:
        from app.services.collection import due_configs, execute_run

        db = SessionLocal()
        try:
            for config in due_configs(db):
                try:
                    self.runs_started += 1
                    execute_run(db, config, trigger="schedule")
                except Exception:
                    log.exception("Scheduled source failed: %s", config.name)
                    db.rollback()
        finally:
            db.close()

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.running = False

    def stats(self) -> dict[str, int | bool]:
        return {"running": self.running, "ticks": self.ticks, "runs_started": self.runs_started}


collection_scheduler = CollectionScheduler()
