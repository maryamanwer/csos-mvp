"""Correlate normalized source evidence into the CSOS Cyber Knowledge Graph."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from app.connectors.models import CollectionResult
from app.graph.neo4j_client import neo4j_client

_RELATIONSHIPS = {"CONNECTS_TO", "DEPENDS_ON", "HOSTS", "COMMUNICATES_WITH", "ROUTES_TO"}
_SOURCE_TRUST = {
    "agent": 50, "ssh_network": 45, "snmp": 40, "nmap": 30,
    "edr_xdr_api": 45, "cmdb_api": 45, "cloud_api": 40,
    "syslog": 15, "csv": 20,
}
_TRUSTED_PROPERTIES = {
    "vendor", "model", "os_name", "os_version", "operating_system",
    "serial_number", "location", "edr_status", "edr_product",
    "edr_agent_version", "managed_status",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding_identity(connector_key: str, finding) -> str:
    if finding.cve_id:
        return finding.cve_id
    if finding.vendor_finding_id:
        return f"{connector_key}:{finding.vendor_finding_id}"
    material = f"{connector_key}|{finding.title}|{finding.port or ''}|{finding.service or ''}"
    return f"csos:{hashlib.sha256(material.encode()).hexdigest()[:24]}"


class NetworkGraphWriter:
    def __init__(self, client=None) -> None:
        self.client = client or neo4j_client

    def _match_asset(self, asset) -> list[dict]:
        rows = self.client.run(
            "MATCH (a:Asset {source_ref: $source_ref}) RETURN a.id AS id, coalesce(a.confidence, 0) AS confidence",
            {"source_ref": asset.source_ref},
        )
        if rows:
            return rows
        return self.client.run(
            "MATCH (a:Asset) WHERE ($serial IS NOT NULL AND a.serial_number = $serial) "
            "OR ($mac IS NOT NULL AND a.mac_address = $mac) "
            "OR ($hostname IS NOT NULL AND a.hostname = $hostname) "
            "OR ($ip IS NOT NULL AND a.ip_address = $ip) "
            "RETURN a.id AS id, coalesce(a.confidence, 0) AS confidence LIMIT 1",
            {"serial": asset.serial_number, "mac": asset.mac_address, "hostname": asset.hostname or asset.name, "ip": asset.ip_address},
        )

    def upsert_assets(self, result: CollectionResult) -> dict[str, str]:
        identifiers: dict[str, str] = {}
        source_trust = _SOURCE_TRUST.get(result.connector_key, 25)
        for asset in result.assets:
            if not asset.source_ref:
                continue
            trust = 5 if "discovered" in asset.tags else source_trust
            properties = asset.graph_properties()
            properties["data_sources"] = sorted(set(asset.data_sources + [result.connector_key]))
            existing = self._match_asset(asset)
            previous_trust = int(existing[0].get("confidence", 0)) if existing else -1
            if existing:
                asset_id = existing[0]["id"]
                self.client.run(
                    "MATCH (a:Asset {id: $id}) SET a.source_ref = coalesce(a.source_ref, $source_ref), "
                    "a.last_seen = $now, a.updated_at = $now, "
                    "a.confidence = CASE WHEN coalesce(a.confidence,0) < $trust THEN $trust ELSE a.confidence END, "
                    "a.data_sources = reduce(out=[], item IN coalesce(a.data_sources,[]) + $sources | CASE WHEN item IN out THEN out ELSE out + item END) "
                    "RETURN a.id AS id",
                    {"id": asset_id, "source_ref": asset.source_ref, "now": _utc_now(), "trust": trust, "sources": properties["data_sources"]},
                )
            else:
                asset_id = str(uuid.uuid4())
                rows = self.client.run(
                    "MERGE (a:Asset {source_ref: $source_ref}) "
                    "ON CREATE SET a.id=$id, a.created_at=$now, a += $properties "
                    "SET a.updated_at=$now, a.last_seen=$now, a.confidence=$trust "
                    "RETURN a.id AS id",
                    {"source_ref": asset.source_ref, "id": asset_id, "now": _utc_now(), "trust": trust, "properties": properties},
                )
                if rows:
                    asset_id = rows[0]["id"]
            identifiers[asset.source_ref] = asset_id
            if previous_trust < 0:
                continue
            ordinary = {key: value for key, value in properties.items() if key not in _TRUSTED_PROPERTIES and key != "data_sources"}
            if ordinary and trust >= previous_trust:
                self.client.run(
                    "MATCH (a:Asset {id: $id}) SET a += $values",
                    {"id": asset_id, "values": ordinary},
                )
            authoritative = {key: value for key, value in properties.items() if key in _TRUSTED_PROPERTIES}
            if authoritative and trust >= previous_trust:
                self.client.run(
                    "MATCH (a:Asset {id: $id}) SET a += $props",
                    {"id": asset_id, "props": authoritative},
                )
        return identifiers

    def upsert_interfaces(self, result: CollectionResult) -> int:
        count = 0
        for interface in result.interfaces:
            rows = self.client.run(
                "MATCH (a:Asset {source_ref: $asset_ref}) "
                "MERGE (i:NetworkInterface {key: $key}) "
                "ON CREATE SET i.id=$id, i.created_at=$now "
                "SET i += $properties, i.updated_at=$now "
                "MERGE (a)-[:HAS_INTERFACE]->(i) RETURN i.id AS id",
                {"asset_ref": interface.asset_ref, "key": interface.key, "id": str(uuid.uuid4()), "now": _utc_now(), "properties": interface.graph_properties()},
            )
            if not rows:
                continue
            count += 1
            if interface.subnet_cidr:
                self.client.run(
                    "MATCH (i:NetworkInterface {key:$key}) MERGE (s:Subnet {cidr:$cidr}) "
                    "ON CREATE SET s.id=$id MERGE (i)-[:IN_SUBNET]->(s)",
                    {"key": interface.key, "cidr": interface.subnet_cidr, "id": str(uuid.uuid4())},
                )
            if interface.vlan_id:
                self.client.run(
                    "MATCH (i:NetworkInterface {key:$key}) MERGE (v:VLAN {vlan_id:$vlan}) "
                    "ON CREATE SET v.id=$id MERGE (i)-[:MEMBER_OF]->(v)",
                    {"key": interface.key, "vlan": str(interface.vlan_id), "id": str(uuid.uuid4())},
                )
        return count

    def upsert_links(self, result: CollectionResult) -> int:
        count = 0
        for link in result.links:
            if link.source_ref == link.target_ref:
                continue
            if link.link_type not in _RELATIONSHIPS:
                result.errors.append(f"Unsupported relationship type: {link.link_type}")
                continue
            rows = self.client.run(
                f"MATCH (source:Asset {{source_ref:$source_ref}}) MATCH (target:Asset {{source_ref:$target_ref}}) "
                f"MERGE (source)-[rel:{link.link_type}]->(target) "
                "ON CREATE SET rel.id=$id, rel.created_at=$now SET rel += $properties, rel.last_seen=$now RETURN rel.id AS id",
                {"source_ref": link.source_ref, "target_ref": link.target_ref, "id": str(uuid.uuid4()), "now": _utc_now(), "properties": link.graph_properties()},
            )
            count += len(rows)
        return count

    def upsert_vulnerabilities(self, result: CollectionResult) -> int:
        count = 0
        for finding in result.vulnerabilities:
            identity = _finding_identity(result.connector_key, finding)
            rows = self.client.run(
                "MERGE (v:Vulnerability {identity: $identity}) "
                "ON CREATE SET v.id=$id, v.created_at=$now "
                "SET v.title=$title, v.cve_id=$cve, v.severity=$severity, v.cvss_score=$cvss, "
                "v.status=$status, v.description=$description, v.port=$port, v.service=$service, "
                "v.first_detected=coalesce(v.first_detected,$first,$now), v.last_seen=coalesce($last,$now), "
                "v.sla_due_at=$sla, v.recommended_remediation=$remediation, v.vendor_finding_id=$vendor_id, "
                "v.data_sources=$sources, v.updated_at=$now RETURN v.id AS id",
                {
                    "identity": identity, "id": str(uuid.uuid4()), "now": _utc_now(),
                    "title": finding.title, "cve": finding.cve_id, "severity": finding.severity,
                    "cvss": finding.cvss_score, "status": finding.status, "description": finding.description,
                    "port": finding.port, "service": finding.service, "first": finding.first_detected,
                    "last": finding.last_seen, "sla": finding.sla_due_at,
                    "remediation": finding.recommended_remediation, "vendor_id": finding.vendor_finding_id,
                    "sources": sorted(set(finding.data_sources + [result.connector_key])),
                },
            )
            if not rows:
                continue
            count += 1
            for asset_ref in finding.asset_refs:
                self.client.run(
                    "MATCH (a:Asset {source_ref:$asset_ref}) MATCH (v:Vulnerability {identity:$identity}) "
                    "MERGE (a)-[:HAS_VULNERABILITY]->(v)",
                    {"asset_ref": asset_ref, "identity": identity},
                )
        return count

    def write_events(self, result: CollectionResult, retain: int = 5000) -> int:
        events = [
            {
                "id": str(uuid.uuid4()), "message": event.message[:4000],
                "source_ref": event.source_ref, "source_ip": event.source_ip,
                "severity": event.severity, "facility": event.facility,
                "hostname": event.hostname, "app_name": event.app_name,
                "timestamp": event.timestamp,
            }
            for event in result.events if event.message
        ]
        if not events:
            return 0
        self.client.run(
            "UNWIND $events AS item CREATE (e:Event) SET e=item "
            "WITH e OPTIONAL MATCH (a:Asset {source_ref:e.source_ref}) FOREACH (_ IN CASE WHEN a IS NULL THEN [] ELSE [1] END | MERGE (a)-[:GENERATED]->(e))",
            {"events": events},
        )
        self.client.run(
            "MATCH (e:Event) WITH e ORDER BY e.timestamp DESC SKIP $retain DETACH DELETE e",
            {"retain": retain},
        )
        return len(events)

    def write(self, result: CollectionResult) -> dict[str, int]:
        return {
            "assets": len(self.upsert_assets(result)),
            "interfaces": self.upsert_interfaces(result),
            "links": self.upsert_links(result),
            "vulnerabilities": self.upsert_vulnerabilities(result),
            "events": self.write_events(result),
        }


network_writer = NetworkGraphWriter()
