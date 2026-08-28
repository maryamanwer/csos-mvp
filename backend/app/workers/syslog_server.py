"""Dedicated Syslog listener.

Runs as its own worker process with asyncio servers on UDP and TCP. Messages are
buffered and flushed to the graph in batches, because a busy network produces
thousands of lines a minute and a graph write per line would be pathological.

Ports default to 5514 rather than 514: binding below 1024 needs root, and the
container should not run as root. Docker maps 514 to 5514 externally, so
devices still send to the port they expect.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from app.connectors.models import CollectedEvent
from app.connectors.syslog import events_to_result, parse_syslog_line
from app.core.config import settings

logger = logging.getLogger(__name__)

#: Flush when either threshold is reached, whichever comes first.
BATCH_SIZE = 200
FLUSH_SECONDS = 5.0
#: Hard ceiling so a log storm cannot exhaust memory faster than we can write.
MAX_BUFFER = 20_000


class SyslogCollector:
    """Buffers received lines and flushes them to the graph."""

    def __init__(self, writer=None) -> None:
        self._buffer: list[CollectedEvent] = []
        self._lock = asyncio.Lock()
        self._writer = writer
        self.received = 0
        self.dropped = 0
        self.written = 0

    def _resolve_writer(self):
        if self._writer is None:
            from app.graph.network_writer import network_writer

            self._writer = network_writer
        return self._writer

    async def add(self, line: str, source_ip: str | None) -> None:
        if len(line.encode("utf-8", errors="ignore")) > settings.SYSLOG_MAX_MESSAGE_BYTES:
            self.dropped += 1
            return
        event = parse_syslog_line(line, source_ip)
        if not event.message:
            return
        async with self._lock:
            if len(self._buffer) >= MAX_BUFFER:
                self.dropped += 1
                return
            self._buffer.append(event)
            self.received += 1
            should_flush = len(self._buffer) >= BATCH_SIZE
        if should_flush:
            await self.flush()

    async def flush(self) -> int:
        async with self._lock:
            if not self._buffer:
                return 0
            batch, self._buffer = self._buffer, []

        result = events_to_result(batch)
        try:
            written = await asyncio.to_thread(self._resolve_writer().write, result)
            self.written += written.get("events", 0)
            return written.get("events", 0)
        except Exception as exc:  # noqa: BLE001 - never let a write kill the listener
            logger.error("Unable to write Syslog batch: %s", exc)
            return 0

    def stats(self) -> dict[str, int]:
        return {
            "received": self.received,
            "written": self.written,
            "dropped": self.dropped,
            "buffered": len(self._buffer),
        }


class _UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, collector: SyslogCollector) -> None:
        self._collector = collector

    def datagram_received(self, data: bytes, addr) -> None:
        line = data.decode("utf-8", errors="replace")
        asyncio.create_task(self._collector.add(line, addr[0] if addr else None))


async def _handle_tcp(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    collector: SyslogCollector,
) -> None:
    peer = writer.get_extra_info("peername")
    source_ip = peer[0] if peer else None
    try:
        while True:
            # Bounded read: an endless line from a misbehaving sender must not
            # be buffered without limit.
            try:
                line = await reader.readuntil(b"\n")
            except asyncio.IncompleteReadError as exc:
                line = exc.partial
                if not line:
                    break
            except asyncio.LimitOverrunError:
                await reader.read(settings.SYSLOG_MAX_MESSAGE_BYTES)
                continue
            if not line:
                break
            await collector.add(line.decode("utf-8", errors="replace"), source_ip)
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        writer.close()


class SyslogService:
    """Owns the sockets and the periodic flush task."""

    def __init__(self) -> None:
        self.collector = SyslogCollector()
        self._transport = None
        self._tcp_server: asyncio.AbstractServer | None = None
        self._flush_task: asyncio.Task | None = None
        self.running = False

    async def start(self) -> None:
        if self.running or not settings.SYSLOG_ENABLED:
            return

        loop = asyncio.get_running_loop()
        host = settings.SYSLOG_BIND_ADDRESS

        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: _UDPProtocol(self.collector),
                local_addr=(host, settings.SYSLOG_UDP_PORT),
            )
            logger.info("Syslog listener is accepting UDP on %s:%s", host, settings.SYSLOG_UDP_PORT)
        except OSError as exc:
            logger.error("Unable to open Syslog UDP port: %s", exc)

        try:
            self._tcp_server = await asyncio.start_server(
                lambda r, w: _handle_tcp(r, w, self.collector),
                host,
                settings.SYSLOG_TCP_PORT,
                limit=65536,
            )
            logger.info("Syslog listener is accepting TCP on %s:%s", host, settings.SYSLOG_TCP_PORT)
        except OSError as exc:
            logger.error("Unable to open Syslog TCP port: %s", exc)

        self._flush_task = asyncio.create_task(self._flush_loop())
        self.running = True

    async def _flush_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(FLUSH_SECONDS)
                await self.collector.flush()
            except asyncio.CancelledError:
                await self.collector.flush()
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Syslog flush loop error: %s", exc)

    async def stop(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        if self._transport:
            self._transport.close()
        if self._tcp_server:
            self._tcp_server.close()
            await self._tcp_server.wait_closed()
        self.running = False


syslog_service = SyslogService()


def parse_lines(lines: Iterable[str], source_ip: str | None = None):
    """Convenience wrapper used by tests and the HTTP batch endpoint."""
    return [parse_syslog_line(line, source_ip) for line in lines]
