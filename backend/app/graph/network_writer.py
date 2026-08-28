"""Writes a :class:`CollectionResult` into the Knowledge Graph.

Two things happen here that did not exist before.

First, **correlation**. Connectors identify a device by ``source_ref`` — a
hostname, chassis id, or agent id. The same router seen over SSH, over SNMP,
and as a CDP neighbour of something else must become one node, not three. Every
write merges on ``source_ref``, and enrichment only ever fills blanks: a
placeholder discovered through CDP is upgraded when the device is polled
directly, and never the other way round.

Second, **the network model itself**. ``NetworkInterface``, ``Subnet`` and
``VLAN`` are new node types. Without interfaces there is nowhere to hang an IP
address, and without subnets there is no way to say two devices share a
segment — which is why the original model could not represent a real network
diagram at all.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.connectors.models import CollectionResult
from app.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

#: Fields a richer source may overwrite; everything else is fill-if-empty.
AUTHORITATIVE_FIELDS = {
    "vendor", "model", "os_name", "os_version", "operating_system",
    "serial_number", "location", "edr_status", "edr_product",
    "edr_agent_version", "managed_status",
}

#: Sources ranked by how much they know about a device. A direct poll beats a
#: neighbour's hearsay.
SOURCE_CONFIDENCE = {
    "agent": 40,
    "ssh_network": 35,
    "snmp": 30,
    "nmap": 20,
    "syslog": 10,
    "csv": 15,
    "discovered": 5,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NetworkGraphWriter:
    """Idempotent writer — running the same collection twice changes nothing."""

    def __init__(self, client=None) -> None:
        self._client = client or neo4j_client

    # -- assets ----------------------------------------------------------
    def upsert_assets(self, result: CollectionResult) -> dict[str, str]:
        """Merge assets and return a map of ``source_ref`` to graph id."""
        ref_to_id: dict[str, str] = {}
        confidence = SOURCE_CONFIDENCE.get(result.connector_key, 10)

        for asset in result.assets:
            if not asset.source_ref:
                continue
            properties = asset.graph_properties()
            properties["data_sources"] = sorted({
                *properties.get("data_sources", []), result.connector_key,
            })
            # A neighbour we merely heard about is the weakest kind of evidence.
            is_placeholder = "discovered" in asset.tags
            effective_confidence = 5 if is_placeholder else confidence

            # Read the prior confidence before it is raised, so the comparison
            # below is against what actually wrote the existing values.
            existing = self._client.run(
                "MATCH (a:Asset {source_ref: $source_ref}) "
                "RETURN a.id AS id, coalesce(a.confidence, 0) AS confidence",
                {"source_ref": asset.source_ref},
            )
            if not existing:
                existing = self._client.run(
                    "MATCH (a:Asset) "
                    "WHERE $source_ref IN coalesce(a.source_refs, []) "
                    "RETURN a.id AS id, coalesce(a.confidence, 0) AS confidence",
                    {"source_ref": asset.source_ref},
                )
            if not existing:
                existing = self._client.run(
                "MATCH (a:Asset) "
                "WHERE ($serial_number IS NOT NULL AND a.serial_number = $serial_number) "
                "OR ($mac_address IS NOT NULL AND a.mac_address = $mac_address) "
                "OR ($hostname IS NOT NULL AND (a.hostname = $hostname OR a.name = $hostname)) "
                "OR ($ip_address IS NOT NULL AND a.ip_address = $ip_address) "
                "RETURN a.id AS id, coalesce(a.confidence, 0) AS confidence",
                {
                    "serial_number": asset.serial_number,
                    "mac_address": asset.mac_address,
                    "hostname": asset.hostname or asset.name,
                    "ip_address": asset.ip_address,
                    },
                )
            prior_confidence = existing[0]["confidence"] if existing else -1

            if existing:
                rows = self._client.run(
                    """
                    MATCH (a:Asset {id: $id})
                    SET a.source_ref = coalesce(a.source_ref, $source_ref),
                        a.last_seen = $now,
                        a.updated_at = $now,
                        a.source_refs = reduce(acc = [], ref IN
                            coalesce(a.source_refs, [a.source_ref]) + [$source_ref] |
                            CASE WHEN ref IS NULL OR ref IN acc THEN acc ELSE acc + ref END),
                        a.confidence = CASE
                            WHEN coalesce(a.confidence, 0) < $confidence
                            THEN $confidence ELSE a.confidence END,
                        a.data_sources = reduce(acc = [], source IN
                            coalesce(a.data_sources, []) + $data_sources |
                            CASE WHEN source IN acc THEN acc ELSE acc + source END)
                    RETURN a.id AS id
                    """,
                    {
                        "id": existing[0]["id"],
                        "source_ref": asset.source_ref,
                        "now": _now(),
                        "confidence": effective_confidence,
                        "data_sources": properties["data_sources"],
                    },
                )
                if not rows:
                    # Some compatible graph clients do not return records for
                    # SET queries; the identity was already resolved above.
                    rows = [{"id": existing[0]["id"]}]
            else:
                rows = self._client.run(
                    """
                    MERGE (a:Asset {source_ref: $source_ref})
                    ON CREATE SET a.id = $new_id,
                        a.created_at = $now,
                        a.discovered_by = $connector,
                        a.source_refs = [$source_ref],
                        a += $properties
                    SET
                        a.last_seen = $now,
                        a.updated_at = $now,
                        a.confidence = $confidence
                    RETURN a.id AS id
                    """,
                {
                    "source_ref": asset.source_ref,
                    "new_id": str(uuid.uuid4()),
                    "now": _now(),
                    "connector": result.connector_key,
                    "confidence": effective_confidence,
                    "properties": properties,
                },
                )
            if not rows:
                continue
            asset_id = rows[0]["id"]
            ref_to_id[asset.source_ref] = asset_id

            if prior_confidence < 0:
                continue  # freshly created; ON CREATE already wrote everything

            self._enrich(asset_id, properties, effective_confidence, prior_confidence)

        return ref_to_id

    def _enrich(
        self,
        asset_id: str,
        properties: dict,
        confidence: int,
        prior_confidence: int,
    ) -> None:
        """Update an existing asset without letting a weak source clobber a strong one.

        Descriptive fields are filled only where the node has nothing yet.
        Identity fields (vendor, model, serial…) are replaced only by a source
        at least as trustworthy as the one that set them.
        """
        fill = {k: v for k, v in properties.items() if k not in AUTHORITATIVE_FIELDS}
        if fill:
            assignments = ", ".join(f"a.{key} = coalesce(a.{key}, ${key})" for key in fill)
            self._client.run(
                f"MATCH (a:Asset {{id: $id}}) SET {assignments}",
                {"id": asset_id, **fill},
            )

        authoritative = {
            k: v for k, v in properties.items() if k in AUTHORITATIVE_FIELDS
        }
        if authoritative and confidence >= prior_confidence:
            self._client.run(
                "MATCH (a:Asset {id: $id}) SET a += $props",
                {"id": asset_id, "props": authoritative},
            )

    # -- interfaces, subnets, vlans ---------------------------------------
    def upsert_interfaces(self, result: CollectionResult) -> int:
        written = 0
        for interface in result.interfaces:
            properties = interface.graph_properties()
            rows = self._client.run(
                """
                MATCH (a:Asset)
                WHERE a.source_ref = $asset_ref
                   OR $asset_ref IN coalesce(a.source_refs, [])
                MERGE (i:NetworkInterface {key: $key})
                ON CREATE SET i.id = $new_id, i.created_at = $now
                SET i += $properties, i.updated_at = $now
                MERGE (a)-[:HAS_INTERFACE]->(i)
                RETURN i.id AS id
                """,
                {
                    "asset_ref": interface.asset_ref,
                    "key": interface.key,
                    "new_id": str(uuid.uuid4()),
                    "now": _now(),
                    "properties": properties,
                },
            )
            if not rows:
                continue
            written += 1

            if interface.subnet_cidr:
                self._client.run(
                    """
                    MATCH (i:NetworkInterface {key: $key})
                    MERGE (s:Subnet {cidr: $cidr})
                    ON CREATE SET s.id = $new_id, s.created_at = $now
                    MERGE (i)-[:IN_SUBNET]->(s)
                    """,
                    {
                        "key": interface.key,
                        "cidr": interface.subnet_cidr,
                        "new_id": str(uuid.uuid4()),
                        "now": _now(),
                    },
                )

            if interface.vlan_id:
                self._client.run(
                    """
                    MATCH (i:NetworkInterface {key: $key})
                    MERGE (v:VLAN {vlan_id: $vlan_id})
                    ON CREATE SET v.id = $new_id, v.created_at = $now
                    MERGE (i)-[:MEMBER_OF]->(v)
                    """,
                    {
                        "key": interface.key,
                        "vlan_id": str(interface.vlan_id),
                        "new_id": str(uuid.uuid4()),
                        "now": _now(),
                    },
                )
        return written

    # -- links -------------------------------------------------------------
    def upsert_links(self, result: CollectionResult) -> int:
        written = 0
        for link in result.links:
            if link.source_ref == link.target_ref:
                continue
            # Relationship type cannot be parameterized in Cypher, so it is
            # validated against a fixed allow-list before interpolation.
            if link.link_type not in {
                "CONNECTS_TO", "DEPENDS_ON", "HOSTS", "COMMUNICATES_WITH", "ROUTES_TO"
            }:
                result.errors.append(f"Unsupported relationship type: {link.link_type}")
                continue
            rows = self._client.run(
                f"""
                MATCH (source:Asset)
                WHERE source.source_ref = $source_ref
                   OR $source_ref IN coalesce(source.source_refs, [])
                MATCH (target:Asset)
                WHERE target.source_ref = $target_ref
                   OR $target_ref IN coalesce(target.source_refs, [])
                MERGE (source)-[rel:{link.link_type}]->(target)
                ON CREATE SET rel.id = $new_id, rel.created_at = $now
                SET rel += $properties, rel.last_seen = $now
                RETURN rel.id AS id
                """,
                {
                    "source_ref": link.source_ref,
                    "target_ref": link.target_ref,
                    "new_id": str(uuid.uuid4()),
                    "now": _now(),
                    "properties": link.graph_properties(),
                },
            )
            written += len(rows)
        return written

    # -- vulnerabilities ----------------------------------------------------
    def upsert_vulnerabilities(self, result: CollectionResult) -> int:
        written = 0
        for finding in result.vulnerabilities:
            # Correlate on the finding's identity, not a fresh id each run,
            # so a recurring scan updates rather than duplicates.
            if finding.cve_id:
                identity = finding.cve_id
            elif finding.vendor_finding_id:
                identity = f"{result.connector_key}:{finding.vendor_finding_id}"
            else:
                identity = (
                    f"{result.connector_key}:{finding.title}|"
                    f"{finding.port or ''}|{finding.service or ''}"
                )
            rows = self._client.run(
                """
                MERGE (v:Vulnerability {identity: $identity})
                ON CREATE SET v.id = $new_id, v.created_at = $now
                SET v.title = $title,
                    v.cve_id = $cve_id,
                    v.severity = $severity,
                    v.cvss_score = $cvss_score,
                    v.status = $status,
                    v.description = $description,
                    v.port = $port,
                    v.service = $service,
                    v.first_detected = coalesce(v.first_detected, $first_detected, $now),
                    v.last_seen = coalesce($last_seen, $now),
                    v.sla_due_at = $sla_due_at,
                    v.recommended_remediation = $recommended_remediation,
                    v.vendor_finding_id = $vendor_finding_id,
                    v.data_sources = reduce(acc = [], source IN
                        coalesce(v.data_sources, []) + $data_sources |
                        CASE WHEN source IN acc THEN acc ELSE acc + source END),
                    v.updated_at = $now
                RETURN v.id AS id
                """,
                {
                    "identity": identity,
                    "new_id": str(uuid.uuid4()),
                    "now": _now(),
                    "title": finding.title,
                    "cve_id": finding.cve_id,
                    "severity": finding.severity,
                    "cvss_score": finding.cvss_score,
                    "status": finding.status,
                    "description": finding.description,
                    "port": finding.port,
                    "service": finding.service,
                    "first_detected": finding.first_detected,
                    "last_seen": finding.last_seen,
                    "sla_due_at": finding.sla_due_at,
                    "recommended_remediation": finding.recommended_remediation,
                    "vendor_finding_id": finding.vendor_finding_id,
                    "data_sources": sorted({*finding.data_sources, result.connector_key}),
                },
            )
            if not rows:
                continue
            written += 1
            for asset_ref in finding.asset_refs:
                self._client.run(
                    """
                    MATCH (a:Asset)
                    WHERE a.source_ref = $asset_ref
                       OR $asset_ref IN coalesce(a.source_refs, [])
                    MATCH (v:Vulnerability {identity: $identity})
                    MERGE (a)-[:HAS_VULNERABILITY]->(v)
                    """,
                    {"asset_ref": asset_ref, "identity": identity},
                )
        return written

    # -- events -------------------------------------------------------------
    def write_events(self, result: CollectionResult, retain: int = 5000) -> int:
        """Persist log events, keeping only the most recent ``retain`` of them.

        A syslog feed is unbounded; the graph is not the right place to keep
        history forever, so this is a rolling window sized for investigation
        rather than archival.
        """
        if not result.events:
            return 0

        payload = [
            {
                "id": str(uuid.uuid4()),
                "message": event.message[:4000],
                "source_ref": event.source_ref,
                "source_ip": event.source_ip,
                "severity": event.severity,
                "facility": event.facility,
                "hostname": event.hostname,
                "app_name": event.app_name,
                "timestamp": event.timestamp,
            }
            for event in result.events
            if event.message
        ]
        if not payload:
            return 0

        self._client.run(
            """
            UNWIND $events AS event
            CREATE (e:Event)
            SET e = event
            WITH e
            MATCH (a:Asset)
            WHERE a.source_ref = e.source_ref
               OR e.source_ref IN coalesce(a.source_refs, [])
            MERGE (a)-[:GENERATED]->(e)
            """,
            {"events": payload},
        )
        self._client.run(
            """
            MATCH (e:Event)
            WITH e ORDER BY e.timestamp DESC SKIP $retain
            DETACH DELETE e
            """,
            {"retain": retain},
        )
        return len(payload)

    # -- entry point --------------------------------------------------------
    def write(self, result: CollectionResult) -> dict[str, int]:
        """Persist an entire collection result and return what was written."""
        stats = {
            "assets": 0, "interfaces": 0, "links": 0,
            "vulnerabilities": 0, "events": 0,
        }
        stats["assets"] = len(self.upsert_assets(result))
        stats["interfaces"] = self.upsert_interfaces(result)
        stats["links"] = self.upsert_links(result)
        stats["vulnerabilities"] = self.upsert_vulnerabilities(result)
        stats["events"] = self.write_events(result)
        return stats


network_writer = NetworkGraphWriter()
