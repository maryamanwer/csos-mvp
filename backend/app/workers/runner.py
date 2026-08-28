"""Run collection workers as dedicated processes, never inside API replicas."""
from __future__ import annotations

import argparse
import asyncio
import signal

from app.workers.scheduler import collection_scheduler
from app.workers.syslog_server import syslog_service


async def _wait_for_shutdown() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows development runtime
            pass
    await stop.wait()


async def run(mode: str) -> None:
    service = collection_scheduler if mode == "scheduler" else syslog_service
    await service.start()
    try:
        await _wait_for_shutdown()
    finally:
        await service.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="CSOS collection worker")
    parser.add_argument("mode", choices=("scheduler", "syslog"))
    args = parser.parse_args()
    asyncio.run(run(args.mode))


if __name__ == "__main__":
    main()
