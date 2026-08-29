"""Bounded UDP/TCP Syslog receiver for the CSOS collection worker."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from app.connectors.models import CollectedEvent
from app.connectors.syslog import events_to_result, parse_syslog_line
from app.core.config import settings

log = logging.getLogger(__name__)
_BATCH_LIMIT = 200
_BUFFER_LIMIT = 20_000
_FLUSH_INTERVAL = 5.0


class SyslogCollector:
    def __init__(self, writer=None) -> None:
        self._writer = writer
        self._pending: list[CollectedEvent] = []
        self._lock = asyncio.Lock()
        self.received = 0
        self.written = 0
        self.dropped = 0

    def _graph_writer(self):
        if self._writer is None:
            from app.graph.network_writer import network_writer
            self._writer = network_writer
        return self._writer

    async def add(self, line: str, source_ip: str | None) -> None:
        if len(line.encode(errors="ignore")) > settings.SYSLOG_MAX_MESSAGE_BYTES:
            self.dropped += 1
            return
        event = parse_syslog_line(line, source_ip)
        if not event.message:
            return
        async with self._lock:
            if len(self._pending) >= _BUFFER_LIMIT:
                self.dropped += 1
                return
            self._pending.append(event)
            self.received += 1
            full = len(self._pending) >= _BATCH_LIMIT
        if full:
            await self.flush()

    async def flush(self) -> int:
        async with self._lock:
            if not self._pending:
                return 0
            batch = self._pending
            self._pending = []
        try:
            outcome = await asyncio.to_thread(self._graph_writer().write, events_to_result(batch))
            count = int(outcome.get("events", 0))
            self.written += count
            return count
        except Exception:
            log.exception("Could not write a Syslog batch")
            self.dropped += len(batch)
            return 0

    def stats(self) -> dict[str, int]:
        return {"received": self.received, "written": self.written, "dropped": self.dropped, "buffered": len(self._pending)}


class _UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, collector: SyslogCollector) -> None:
        self.collector = collector

    def datagram_received(self, data: bytes, addr) -> None:
        source_ip = addr[0] if addr else None
        asyncio.create_task(self.collector.add(data.decode(errors="replace"), source_ip))


async def _handle_tcp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, collector: SyslogCollector) -> None:
    peer = writer.get_extra_info("peername")
    source_ip = peer[0] if peer else None
    try:
        while line := await reader.readline():
            await collector.add(line.decode(errors="replace"), source_ip)
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


class SyslogService:
    def __init__(self) -> None:
        self.collector = SyslogCollector()
        self.running = False
        self._udp = None
        self._tcp: asyncio.AbstractServer | None = None
        self._flusher: asyncio.Task | None = None

    async def start(self) -> None:
        if self.running or not settings.SYSLOG_ENABLED:
            return
        loop = asyncio.get_running_loop()
        self._udp, _ = await loop.create_datagram_endpoint(
            lambda: _UDPProtocol(self.collector),
            local_addr=(settings.SYSLOG_BIND_ADDRESS, settings.SYSLOG_UDP_PORT),
        )
        self._tcp = await asyncio.start_server(
            lambda reader, writer: _handle_tcp(reader, writer, self.collector),
            settings.SYSLOG_BIND_ADDRESS, settings.SYSLOG_TCP_PORT,
            limit=settings.SYSLOG_MAX_MESSAGE_BYTES,
        )
        self._flusher = asyncio.create_task(self._flush_loop())
        self.running = True

    async def _flush_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(_FLUSH_INTERVAL)
                await self.collector.flush()
            except asyncio.CancelledError:
                await self.collector.flush()
                raise

    async def stop(self) -> None:
        if self._flusher:
            self._flusher.cancel()
            try:
                await self._flusher
            except asyncio.CancelledError:
                pass
        if self._udp:
            self._udp.close()
        if self._tcp:
            self._tcp.close()
            await self._tcp.wait_closed()
        self.running = False


syslog_service = SyslogService()


def parse_lines(lines: Iterable[str], source_ip: str | None = None):
    return [parse_syslog_line(line, source_ip) for line in lines]
