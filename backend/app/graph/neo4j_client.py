"""Neo4j access layer for assets, vulnerabilities, dashboards, and topology."""
import uuid

from neo4j import GraphDatabase

from app.core.config import settings


class Neo4jClient:
    TOPOLOGY_LABELS = (
        "Asset",
        "Identity",
        "Vulnerability",
        "Risk",
        "Control",
        "Policy",
        "Framework",
        "NetworkInterface",
        "NetworkSegment",
        "Subnet",
        "VLAN",
        "Event",
    )
    ASSET_RELATIONSHIP_TYPES = {
        "CONNECTS_TO",
        "CONNECTED_TO",
        "DEPENDS_ON",
        "HOSTS",
        "COMMUNICATES_WITH",
        "PROTECTED_BY",
        "CONNECTED_THROUGH",
    }
    NETWORK_RELATIONSHIPS = {
        "CONNECTS_TO",
        "CONNECTED_TO",
        "COMMUNICATES_WITH",
        "DEPENDS_ON",
        "HOSTS",
        "PROTECTED_BY",
        "PROTECTS",
        "CONNECTED_THROUGH",
        "HAS_INTERFACE",
        "LOCATED_IN",
        "IN_SUBNET",
        "MEMBER_OF",
        "ROUTES_TO",
    }
    VULNERABILITY_RELATIONSHIPS = {"HAS_VULNERABILITY", "CONTRIBUTES_TO"}
    RISK_RELATIONSHIPS = {"AFFECTS", "HAS_RISK", "MITIGATES"}
    IDENTITY_RELATIONSHIPS = {
        "OWNED_BY",
        "OWNS",
        "HAS_ACCESS_TO",
        "ASSOCIATED_WITH",
    }

    def __init__(self):
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

    def close(self):
        self._driver.close()

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    def run(self, query: str, parameters: dict | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def attack_paths(self, max_hops: int = 4, limit: int = 25) -> list[dict]:
        """Rank reachable critical assets using only explicit graph relationships."""
        hops = max(1, min(int(max_hops), 8))
        rows = self.run(
            f"""
            MATCH p=(entry:Asset)-[:CONNECTS_TO|CONNECTED_TO|COMMUNICATES_WITH|DEPENDS_ON|HOSTS|ROUTES_TO*1..{hops}]->(target:Asset)
            WHERE (entry.environment = 'external' OR entry.type IN ['firewall', 'endpoint', 'workstation'])
              AND target.criticality IN ['critical', 'high']
              AND entry.id <> target.id
            OPTIONAL MATCH (target)-[:HAS_VULNERABILITY]->(v:Vulnerability)
            WHERE v.status IN ['open', 'in_progress']
            WITH p, entry, target, collect(DISTINCT properties(v)) AS vulnerabilities
            WITH p, entry, target, vulnerabilities,
                 reduce(score = 0, node IN nodes(p) |
                    score + CASE coalesce(node.criticality, 'low')
                      WHEN 'critical' THEN 25 WHEN 'high' THEN 15
                      WHEN 'medium' THEN 7 ELSE 2 END) AS asset_score
            RETURN entry.id AS source_id, entry.name AS source,
                   target.id AS target_id, target.name AS target,
                   [node IN nodes(p) | {{id: node.id, name: node.name,
                     criticality: node.criticality, type: node.type}}] AS nodes,
                   [rel IN relationships(p) | type(rel)] AS relationships,
                   length(p) AS hops, vulnerabilities,
                   asset_score + reduce(vscore = 0, finding IN vulnerabilities |
                     vscore + toInteger(coalesce(finding.cvss_score, 0))) AS score
            ORDER BY score DESC, hops ASC
            LIMIT $limit
            """,
            {"limit": max(1, min(int(limit), 100))},
        )
        return [
            {
                **row,
                "id": f"{row.get('source_id')}->{row.get('target_id')}",
                "risk_level": (
                    "critical" if row.get("score", 0) >= 70
                    else "high" if row.get("score", 0) >= 45
                    else "medium"
                ),
            }
            for row in rows
        ]

    # ---- Assets ---------------------------------------------------------
    def list_assets(
        self,
        search: str | None = None,
        asset_type: str | None = None,
        criticality: str | None = None,
        environment: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        rows = self.run(
            """
            MATCH (a:Asset)
            WHERE ($search IS NULL OR toLower(a.name) CONTAINS toLower($search)
                   OR toLower(coalesce(a.owner, '')) CONTAINS toLower($search))
              AND ($asset_type IS NULL OR a.type = $asset_type)
              AND ($criticality IS NULL OR a.criticality = $criticality)
              AND ($environment IS NULL OR a.environment = $environment)
            OPTIONAL MATCH (r:Risk)-[:AFFECTS]->(a)
            RETURN properties(a) AS asset, max(toFloat(r.score)) AS risk_score
            ORDER BY asset.name
            SKIP $offset LIMIT $limit
            """,
            {
                "search": search,
                "asset_type": asset_type,
                "criticality": criticality,
                "environment": environment,
                "offset": offset,
                "limit": limit,
            },
        )
        return [self._asset_from_row(row) for row in rows]

    def get_asset(self, asset_id: str) -> dict | None:
        rows = self.run(
            """
            MATCH (a:Asset {id: $id})
            OPTIONAL MATCH (r:Risk)-[:AFFECTS]->(a)
            RETURN properties(a) AS asset, max(toFloat(r.score)) AS risk_score
            """,
            {"id": asset_id},
        )
        return self._asset_from_row(rows[0]) if rows else None

    def create_asset(self, properties: dict) -> dict:
        asset_id = properties.get("id") or f"asset-{uuid.uuid4().hex[:12]}"
        payload = {
            **properties,
            "id": asset_id,
        }
        rows = self.run(
            """
            CREATE (a:Asset)
            SET a = $properties,
                a.created_at = datetime(),
                a.updated_at = datetime()
            RETURN properties(a) AS asset, null AS risk_score
            """,
            {"properties": payload},
        )
        return self._asset_from_row(rows[0])

    def update_asset(self, asset_id: str, properties: dict) -> dict | None:
        rows = self.run(
            """
            MATCH (a:Asset {id: $id})
            SET a += $properties, a.updated_at = datetime()
            WITH a
            OPTIONAL MATCH (r:Risk)-[:AFFECTS]->(a)
            RETURN properties(a) AS asset, max(toFloat(r.score)) AS risk_score
            """,
            {"id": asset_id, "properties": properties},
        )
        return self._asset_from_row(rows[0]) if rows else None

    def delete_asset(self, asset_id: str) -> bool:
        rows = self.run(
            """
            MATCH (a:Asset {id: $id})
            WITH a, count(a) AS found
            DETACH DELETE a
            RETURN found
            """,
            {"id": asset_id},
        )
        return bool(rows and rows[0]["found"])

    def create_asset_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict | None = None,
    ) -> dict | None:
        normalized_type = relationship_type.upper()
        if normalized_type not in self.ASSET_RELATIONSHIP_TYPES:
            raise ValueError("Unsupported asset relationship type")
        rows = self.run(
            f"""
            MATCH (source:Asset {{id: $source_id}}), (target:Asset {{id: $target_id}})
            MERGE (source)-[relationship:{normalized_type}]->(target)
            SET relationship += $properties,
                relationship.updated_at = datetime()
            RETURN elementId(relationship) AS id,
                   source.id AS source_id,
                   target.id AS target_id,
                   type(relationship) AS relationship_type,
                   properties(relationship) AS properties
            """,
            {
                "source_id": source_id,
                "target_id": target_id,
                "properties": properties or {},
            },
        )
        return self._json_safe(rows[0]) if rows else None

    def delete_asset_relationship(self, relationship_id: str) -> bool:
        rows = self.run(
            """
            MATCH ()-[relationship]->()
            WHERE elementId(relationship) = $id
            WITH relationship, count(relationship) AS found
            DELETE relationship
            RETURN found
            """,
            {"id": relationship_id},
        )
        return bool(rows and rows[0]["found"])

    # ---- Vulnerabilities ------------------------------------------------
    def list_vulnerabilities(
        self,
        search: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        asset_id: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        rows = self.run(
            """
            MATCH (v:Vulnerability)
            OPTIONAL MATCH (a:Asset)-[:HAS_VULNERABILITY]->(v)
            WITH v, collect(DISTINCT a.id) AS asset_ids
            WHERE ($search IS NULL OR toLower(v.title) CONTAINS toLower($search)
                   OR toLower(coalesce(v.cve_id, '')) CONTAINS toLower($search))
              AND ($severity IS NULL OR v.severity = $severity)
              AND ($status IS NULL OR v.status = $status)
              AND ($asset_id IS NULL OR $asset_id IN asset_ids)
            RETURN properties(v) AS vulnerability, asset_ids
            ORDER BY CASE vulnerability.severity
                WHEN 'critical' THEN 4 WHEN 'high' THEN 3
                WHEN 'medium' THEN 2 ELSE 1 END DESC, v.title
            SKIP $offset LIMIT $limit
            """,
            {
                "search": search,
                "severity": severity,
                "status": status,
                "asset_id": asset_id,
                "offset": offset,
                "limit": limit,
            },
        )
        return [self._vulnerability_from_row(row) for row in rows]

    def get_vulnerability(self, vulnerability_id: str) -> dict | None:
        rows = self.run(
            """
            MATCH (v:Vulnerability {id: $id})
            OPTIONAL MATCH (a:Asset)-[:HAS_VULNERABILITY]->(v)
            RETURN properties(v) AS vulnerability,
                   collect(DISTINCT a.id) AS asset_ids
            """,
            {"id": vulnerability_id},
        )
        return self._vulnerability_from_row(rows[0]) if rows else None

    def create_vulnerability(self, properties: dict, asset_ids: list[str] | None = None) -> dict:
        vulnerability_id = properties.get("id") or f"vuln-{uuid.uuid4().hex[:12]}"
        payload = {**properties, "id": vulnerability_id}
        rows = self.run(
            """
            CREATE (v:Vulnerability)
            SET v = $properties,
                v.created_at = datetime(),
                v.updated_at = datetime()
            WITH v
            OPTIONAL MATCH (a:Asset) WHERE a.id IN $asset_ids
            FOREACH (_ IN CASE WHEN a IS NULL THEN [] ELSE [1] END |
                MERGE (a)-[:HAS_VULNERABILITY]->(v))
            RETURN properties(v) AS vulnerability,
                   collect(DISTINCT a.id) AS asset_ids
            """,
            {"properties": payload, "asset_ids": asset_ids or []},
        )
        return self._vulnerability_from_row(rows[0])

    def update_vulnerability(
        self,
        vulnerability_id: str,
        properties: dict,
        asset_ids: list[str] | None = None,
    ) -> dict | None:
        rows = self.run(
            """
            MATCH (v:Vulnerability {id: $id})
            SET v += $properties, v.updated_at = datetime()
            WITH v
            OPTIONAL MATCH (a:Asset)-[existing:HAS_VULNERABILITY]->(v)
            WITH v, collect(existing) AS existing_relationships
            FOREACH (relationship IN CASE WHEN $replace_assets THEN existing_relationships ELSE [] END |
                DELETE relationship)
            WITH v
            OPTIONAL MATCH (target:Asset) WHERE target.id IN $asset_ids
            FOREACH (_ IN CASE WHEN target IS NULL THEN [] ELSE [1] END |
                MERGE (target)-[:HAS_VULNERABILITY]->(v))
            WITH v
            OPTIONAL MATCH (linked:Asset)-[:HAS_VULNERABILITY]->(v)
            RETURN properties(v) AS vulnerability,
                   collect(DISTINCT linked.id) AS asset_ids
            """,
            {
                "id": vulnerability_id,
                "properties": properties,
                "asset_ids": asset_ids or [],
                "replace_assets": asset_ids is not None,
            },
        )
        return self._vulnerability_from_row(rows[0]) if rows else None

    def delete_vulnerability(self, vulnerability_id: str) -> bool:
        rows = self.run(
            """
            MATCH (v:Vulnerability {id: $id})
            WITH v, count(v) AS found
            DETACH DELETE v
            RETURN found
            """,
            {"id": vulnerability_id},
        )
        return bool(rows and rows[0]["found"])

    # ---- Correlated security findings ----------------------------------
    @staticmethod
    def _findings_base_query() -> str:
        return """
        MATCH (asset:Asset)-[:HAS_VULNERABILITY]->(vulnerability:Vulnerability)
        OPTIONAL MATCH (vulnerability)-[:CONTRIBUTES_TO]->(vulnerability_risk:Risk)
        OPTIONAL MATCH (asset)<-[:AFFECTS]-(asset_risk:Risk)
        WITH asset, vulnerability,
             reduce(unique_risks = [], item IN
                 collect(DISTINCT vulnerability_risk) + collect(DISTINCT asset_risk) |
                 CASE WHEN item IS NULL OR item IN unique_risks THEN unique_risks
                      ELSE unique_risks + item END) AS risks
        OPTIONAL MATCH (asset_control:Control)-[:APPLIES_TO]->(asset)
        OPTIONAL MATCH (risk_control:Control)-[:MITIGATES]->(related_risk:Risk)
        WHERE related_risk IN risks
        WITH asset, vulnerability, risks,
             reduce(unique_controls = [], item IN
                 collect(DISTINCT asset_control) + collect(DISTINCT risk_control) |
                 CASE WHEN item IS NULL OR item IN unique_controls THEN unique_controls
                      ELSE unique_controls + item END) AS controls,
             reduce(max_score = 0.0, item IN risks |
                 CASE WHEN toFloat(coalesce(item.score, 0)) > max_score
                      THEN toFloat(coalesce(item.score, 0)) ELSE max_score END) AS linked_risk_score
        WITH asset, vulnerability, risks, controls,
             CASE WHEN linked_risk_score > 0 THEN linked_risk_score
                  ELSE toFloat(coalesce(vulnerability.cvss_score, 0)) * 10 END AS risk_score
        WITH asset, vulnerability, risks, controls, risk_score,
             CASE WHEN risk_score >= 70 THEN 'high'
                  WHEN risk_score >= 40 THEN 'medium' ELSE 'low' END AS risk_level,
             CASE coalesce(vulnerability.status, 'open')
                  WHEN 'accepted' THEN 'accepted_risk'
                  WHEN 'mitigated' THEN 'resolved'
                  WHEN 'false_positive' THEN 'resolved'
                  ELSE coalesce(vulnerability.status, 'open') END AS finding_status,
             CASE WHEN asset.edr_status = 'outdated'
                            OR coalesce(asset.edr_agent_outdated, false) THEN 'outdated'
                  WHEN asset.edr_status = 'active' THEN 'covered'
                  ELSE 'missing' END AS edr_coverage,
             reduce(sources = [], source IN
                 coalesce(asset.data_sources, []) + coalesce(vulnerability.data_sources, []) |
                 CASE WHEN source IN sources THEN sources ELSE sources + source END) AS data_sources
        WITH asset, vulnerability, risks, controls, risk_score, risk_level,
             finding_status, edr_coverage, data_sources,
             CASE WHEN vulnerability.sla_due_at IS NULL THEN 'not_set'
                  WHEN finding_status IN ['resolved', 'accepted_risk'] THEN 'completed'
                  WHEN vulnerability.sla_due_at < datetime() THEN 'breached'
                  ELSE 'within_sla' END AS sla_status
        WHERE ($finding_id IS NULL OR vulnerability.id = $finding_id)
          AND ($search IS NULL OR
               toLower(coalesce(vulnerability.cve_id, '')) CONTAINS toLower($search) OR
               toLower(vulnerability.title) CONTAINS toLower($search) OR
               toLower(asset.name) CONTAINS toLower($search) OR
               toLower(coalesce(asset.hostname, '')) CONTAINS toLower($search) OR
               toLower(coalesce(asset.ip_address, '')) CONTAINS toLower($search) OR
               toLower(coalesce(asset.owner, '')) CONTAINS toLower($search))
          AND ($risk_level IS NULL OR risk_level = $risk_level)
          AND ($criticality IS NULL OR asset.criticality = $criticality)
          AND ($severity IS NULL OR vulnerability.severity = $severity)
          AND ($edr_coverage IS NULL OR edr_coverage = $edr_coverage)
          AND ($asset_type IS NULL OR asset.type = $asset_type)
          AND ($owner IS NULL OR
               toLower(coalesce(asset.owner, '')) CONTAINS toLower($owner))
          AND ($status IS NULL OR finding_status = $status)
          AND ($data_source IS NULL OR any(source IN data_sources
               WHERE toLower(source) = toLower($data_source)))
        """

    @staticmethod
    def _finding_params(**filters) -> dict:
        return {
            "finding_id": filters.get("finding_id"),
            "search": filters.get("search"),
            "risk_level": filters.get("risk_level"),
            "criticality": filters.get("criticality"),
            "severity": filters.get("severity"),
            "edr_coverage": filters.get("edr_coverage"),
            "asset_type": filters.get("asset_type"),
            "owner": filters.get("owner"),
            "status": filters.get("status"),
            "data_source": filters.get("data_source"),
        }

    @staticmethod
    def _finding_return_clause() -> str:
        return """
        RETURN vulnerability.id AS finding_id,
               vulnerability.cve_id AS cve_id,
               vulnerability.title AS title,
               asset.id AS asset_id,
               asset.name AS asset_name,
               coalesce(asset.hostname, asset.name) AS preferred_hostname,
               asset.type AS asset_type,
               asset.criticality AS asset_criticality,
               asset.owner AS asset_owner,
               asset.ip_address AS ip_address,
               asset.operating_system AS operating_system,
               coalesce(asset.edr_status, 'unknown') AS edr_status,
               asset.edr_product AS edr_product,
               vulnerability.severity AS severity,
               toFloat(coalesce(vulnerability.cvss_score, 0)) AS cvss_score,
               risk_score, risk_level, finding_status AS status,
               vulnerability.first_detected AS first_detected,
               vulnerability.last_seen AS last_seen,
               vulnerability.sla_due_at AS sla_due_at,
               sla_status,
               CASE WHEN vulnerability.sla_due_at IS NULL THEN null
                    ELSE duration.inDays(datetime(), vulnerability.sla_due_at).days END
                    AS sla_days_remaining,
               data_sources,
               vulnerability.recommended_remediation AS recommended_remediation,
               [control IN controls | control{.id, .name, .status, .source}] AS controls
        """

    def list_security_findings(
        self,
        *,
        search: str | None = None,
        risk_level: str | None = None,
        criticality: str | None = None,
        severity: str | None = None,
        edr_coverage: str | None = None,
        asset_type: str | None = None,
        owner: str | None = None,
        status: str | None = None,
        data_source: str | None = None,
        sort_by: str = "risk_score",
        sort_direction: str = "desc",
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        sort_fields = {
            "finding_id": "coalesce(vulnerability.cve_id, vulnerability.id)",
            "asset_name": "asset.name",
            "asset_type": "asset.type",
            "asset_criticality": "asset.criticality",
            "asset_owner": "asset.owner",
            "severity": "vulnerability.severity",
            "cvss_score": "vulnerability.cvss_score",
            "risk_score": "risk_score",
            "risk_level": "risk_level",
            "status": "finding_status",
            "first_detected": "vulnerability.first_detected",
            "last_seen": "vulnerability.last_seen",
            "sla_due_at": "vulnerability.sla_due_at",
        }
        sort_expression = sort_fields.get(sort_by, "risk_score")
        direction = "ASC" if sort_direction.lower() == "asc" else "DESC"
        params = self._finding_params(
            search=search,
            risk_level=risk_level,
            criticality=criticality,
            severity=severity,
            edr_coverage=edr_coverage,
            asset_type=asset_type,
            owner=owner,
            status=status,
            data_source=data_source,
        )
        count_rows = self.run(
            self._findings_base_query() + " RETURN count(*) AS total",
            params,
        )
        rows = self.run(
            self._findings_base_query()
            + self._finding_return_clause()
            + f" ORDER BY {sort_expression} {direction} SKIP $offset LIMIT $limit",
            {**params, "offset": offset, "limit": limit},
        )
        return {
            "items": [self._json_safe(row) for row in rows],
            "total": int(count_rows[0]["total"] if count_rows else 0),
        }

    def findings_summary(self) -> dict:
        rows = self.run(
            """
            CALL {
                MATCH (:Asset)-[:HAS_VULNERABILITY]->(v:Vulnerability)
                RETURN count(v) AS total_findings,
                       sum(CASE WHEN v.severity = 'critical' THEN 1 ELSE 0 END)
                           AS critical_findings,
                       sum(CASE WHEN v.sla_due_at IS NOT NULL
                                     AND v.sla_due_at < datetime()
                                     AND NOT coalesce(v.status, 'open') IN
                                         ['resolved', 'mitigated', 'accepted', 'accepted_risk']
                                THEN 1 ELSE 0 END) AS sla_breaches
            }
            CALL {
                MATCH (a:Asset)
                WHERE a.criticality IN ['critical', 'high']
                  AND coalesce(a.edr_status, 'missing') <> 'active'
                RETURN count(a) AS critical_assets_without_edr
            }
            CALL {
                MATCH (a:Asset)-[:HAS_VULNERABILITY]->(v:Vulnerability)
                WHERE a.criticality IN ['critical', 'high']
                  AND v.severity IN ['critical', 'high']
                RETURN count(v) AS critical_vulnerabilities_on_critical_assets
            }
            CALL {
                MATCH (a:Asset)
                WHERE a.edr_status = 'outdated'
                   OR coalesce(a.edr_agent_outdated, false)
                RETURN count(a) AS outdated_security_agents
            }
            CALL {
                MATCH (a:Asset)
                WHERE NOT EXISTS { MATCH (:Control)-[:APPLIES_TO]->(a) }
                  AND NOT EXISTS {
                      MATCH (:Control)-[:MITIGATES]->(:Risk)-[:AFFECTS]->(a)
                  }
                RETURN count(a) AS assets_missing_controls
            }
            CALL {
                MATCH (a:Asset)
                WHERE coalesce(a.managed_status, 'unknown') IN ['unknown', 'unmanaged']
                RETURN count(a) AS unmanaged_assets
            }
            RETURN total_findings, critical_findings, sla_breaches,
                   critical_assets_without_edr,
                   critical_vulnerabilities_on_critical_assets,
                   outdated_security_agents, assets_missing_controls, unmanaged_assets
            """
        )
        return self._json_safe(rows[0] if rows else {})

    def get_security_finding(self, finding_id: str, asset_id: str | None = None) -> dict | None:
        params = self._finding_params(finding_id=finding_id)
        rows = self.run(
            self._findings_base_query()
            + " AND ($asset_id IS NULL OR asset.id = $asset_id) "
            + self._finding_return_clause()
            + " LIMIT 1",
            {**params, "asset_id": asset_id},
        )
        if not rows:
            return None
        finding = self._json_safe(rows[0])
        context_rows = self.run(
            """
            MATCH (asset:Asset {id: $asset_id})-[:HAS_VULNERABILITY]->
                  (vulnerability:Vulnerability {id: $finding_id})
            OPTIONAL MATCH (vulnerability)-[:CONTRIBUTES_TO]->(risk:Risk)
            OPTIONAL MATCH (asset)<-[:AFFECTS]-(asset_risk:Risk)
            WITH asset, vulnerability,
                 reduce(unique_risks = [], item IN
                     collect(DISTINCT risk) + collect(DISTINCT asset_risk) |
                     CASE WHEN item IS NULL OR item IN unique_risks THEN unique_risks
                          ELSE unique_risks + item END) AS risks
            OPTIONAL MATCH (asset_control:Control)-[:APPLIES_TO]->(asset)
            OPTIONAL MATCH (risk_control:Control)-[:MITIGATES]->(related_risk:Risk)
            WHERE related_risk IN risks
            WITH asset, vulnerability, risks,
                 reduce(unique_controls = [], item IN
                     collect(DISTINCT asset_control) + collect(DISTINCT risk_control) |
                     CASE WHEN item IS NULL OR item IN unique_controls
                          THEN unique_controls ELSE unique_controls + item END) AS controls
            OPTIONAL MATCH (asset)-[identity_rel:OWNED_BY|OWNS|HAS_ACCESS_TO|ASSOCIATED_WITH]-(identity:Identity)
            OPTIONAL MATCH (asset)-[network_rel:CONNECTS_TO|CONNECTED_TO|COMMUNICATES_WITH|
                           DEPENDS_ON|HOSTS|PROTECTED_BY|PROTECTS|CONNECTED_THROUGH]-(connected:Asset)
            RETURN properties(asset) AS asset,
                   collect(DISTINCT properties(identity)) AS owner_identities,
                   [risk IN risks | properties(risk)] AS risks,
                   [control IN controls | properties(control)] AS controls,
                   collect(DISTINCT connected{.*, relationship: type(network_rel),
                       relationship_properties: properties(network_rel)}) AS connected_assets
            """,
            {"finding_id": finding_id, "asset_id": finding["asset_id"]},
        )
        context = self._json_safe(context_rows[0] if context_rows else {})
        risks = [item for item in context.get("risks", []) if item]
        controls = [item for item in context.get("controls", []) if item]
        identities = [item for item in context.get("owner_identities", []) if item]
        chain = [
            {"from": "Asset", "relationship": "OWNED_BY", "to": "Owner"},
            {"from": "Asset", "relationship": "HAS_VULNERABILITY", "to": "Vulnerability"},
        ]
        if controls:
            chain.append({"from": "Security Control", "relationship": "APPLIES_TO", "to": "Asset"})
        if risks:
            chain.append({"from": "Vulnerability", "relationship": "CONTRIBUTES_TO", "to": "Risk"})
        chain.append({"from": "Risk", "relationship": "REQUIRES", "to": "Remediation"})
        return {
            "finding": finding,
            "asset": context.get("asset") or {},
            "owner_identities": identities,
            "risks": risks,
            "controls": controls,
            "connected_assets": [
                item for item in context.get("connected_assets", []) if item
            ],
            "relationship_chain": chain,
        }

    # ---- Dashboard and risk --------------------------------------------
    def top_risks(self, limit: int = 5) -> list[dict]:
        return self.run(
            """
            MATCH (r:Risk)-[:AFFECTS]->(a:Asset)
            OPTIONAL MATCH (c:Control)-[:MITIGATES]->(r)
            RETURN r, a, collect(c) AS controls
            ORDER BY r.score DESC LIMIT $limit
            """,
            {"limit": limit},
        )

    def executive_summary(self) -> dict:
        counts = self.run(
            """
            CALL { MATCH (a:Asset) RETURN count(a) AS asset_count }
            CALL {
                MATCH (v:Vulnerability)
                WHERE v.status = 'open'
                RETURN count(v) AS open_vulnerability_count
            }
            CALL {
                MATCH (r:Risk)
                WHERE r.status = 'open'
                RETURN coalesce(round(avg(toFloat(r.score)) * 10) / 10, 0) AS overall_risk_score
            }
            RETURN asset_count, open_vulnerability_count, overall_risk_score
            """
        )
        criticality = self.run(
            """
            MATCH (a:Asset)
            RETURN a.criticality AS label, count(a) AS value
            ORDER BY value DESC
            """
        )
        severity = self.run(
            """
            MATCH (v:Vulnerability)
            RETURN v.severity AS label, count(v) AS value
            ORDER BY value DESC
            """
        )
        compliance = self.run(
            """
            MATCH (c:Control)-[:PART_OF]->(f:Framework)
            RETURN f.name AS framework,
                   count(c) AS total_controls,
                   sum(CASE WHEN c.status = 'implemented' THEN 1 ELSE 0 END) AS controls_met
            ORDER BY f.name
            """
        )
        compliance_rows = []
        for row in compliance:
            total = int(row.get("total_controls") or 0)
            met = int(row.get("controls_met") or 0)
            compliance_rows.append(
                {
                    "framework": row.get("framework") or "Unknown",
                    "total_controls": total,
                    "controls_met": met,
                    "coverage_pct": round((met / total * 100) if total else 0, 1),
                }
            )
        coverage = (
            round(
                sum(item["coverage_pct"] for item in compliance_rows)
                / len(compliance_rows),
                1,
            )
            if compliance_rows
            else 0
        )
        top_risks = []
        for row in self.top_risks(limit=5):
            risk = self._json_safe(dict(row["r"]))
            asset = self._json_safe(dict(row["a"]))
            top_risks.append({**risk, "affected_asset_id": asset.get("id")})
        base = counts[0] if counts else {}
        return {
            "overall_risk_score": float(base.get("overall_risk_score") or 0),
            "asset_count": int(base.get("asset_count") or 0),
            "open_vulnerability_count": int(base.get("open_vulnerability_count") or 0),
            "compliance_pct": coverage,
            "asset_criticality": [self._json_safe(row) for row in criticality],
            "vulnerability_severity": [self._json_safe(row) for row in severity],
            "compliance_frameworks": compliance_rows,
            "top_risks": top_risks,
        }

    def investigation_queue(self, limit: int = 100) -> list[dict]:
        rows = self.run(
            """
            CALL {
                MATCH (v:Vulnerability)
                WHERE v.status = 'open'
                OPTIONAL MATCH (a:Asset)-[:HAS_VULNERABILITY]->(v)
                RETURN v.id AS id, 'vulnerability' AS item_type,
                       v.title AS title, v.severity AS severity,
                       v.status AS status, coalesce(v.cvss_score, 0) * 10 AS priority_score,
                       collect(DISTINCT a.id) AS asset_ids,
                       v.cve_id AS reference
                UNION ALL
                MATCH (r:Risk)
                WHERE r.status = 'open'
                OPTIONAL MATCH (r)-[:AFFECTS]->(a:Asset)
                RETURN r.id AS id, 'risk' AS item_type,
                       r.title AS title, r.impact AS severity,
                       r.status AS status, coalesce(r.score, 0) AS priority_score,
                       collect(DISTINCT a.id) AS asset_ids,
                       null AS reference
            }
            RETURN id, item_type, title, severity, status, priority_score, asset_ids, reference
            ORDER BY priority_score DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )
        return [self._json_safe(row) for row in rows]

    # ---- Topology -------------------------------------------------------
    def get_topology(
        self,
        relationship_limit: int = 500,
        node_limit: int = 1000,
        focus_asset_id: str | None = None,
    ) -> dict:
        node_rows = self.run(
            """
        MATCH (entity)
        WHERE any(entity_label IN labels(entity)
                  WHERE entity_label IN $supported_labels)
        OPTIONAL MATCH (risk:Risk)-[:AFFECTS]->(entity)
        OPTIONAL MATCH (entity)-[:HAS_VULNERABILITY]->(vulnerability:Vulnerability)
        WITH entity,
             max(toFloat(coalesce(risk.score, 0))) AS linked_risk_score,
             max(toFloat(coalesce(vulnerability.cvss_score, 0)) * 10) AS vulnerability_score
        RETURN elementId(entity) AS entity_key,
               labels(entity) AS entity_labels,
               properties(entity) AS entity_properties,
               CASE WHEN linked_risk_score > vulnerability_score
                    THEN linked_risk_score ELSE vulnerability_score END AS derived_risk_score
        LIMIT $limit
        """,
            {"limit": node_limit, "supported_labels": list(self.TOPOLOGY_LABELS)},
        )
        relationship_rows = self.run(
            """
        MATCH (source)-[relationship]->(target)
        WHERE any(source_label IN labels(source)
                  WHERE source_label IN $supported_labels)
          AND any(target_label IN labels(target)
                  WHERE target_label IN $supported_labels)
        RETURN elementId(source) AS source_key,
               labels(source) AS source_labels,
               properties(source) AS source_properties,
               elementId(target) AS target_key,
               labels(target) AS target_labels,
               properties(target) AS target_properties,
               elementId(relationship) AS relationship_key,
               type(relationship) AS relationship_type,
               properties(relationship) AS relationship_properties
        LIMIT $limit
        """,
            {
                "limit": relationship_limit,
                "supported_labels": list(self.TOPOLOGY_LABELS),
            },
        )

        nodes: dict[str, dict] = {}
        edges: dict[str, dict] = {}
        supported_labels = set(self.TOPOLOGY_LABELS)

        # Load supported entities independently so a newly seeded or imported
        # node remains visible even before relationships have been created.
        for row in node_rows:
            if not supported_labels.intersection(row["entity_labels"]):
                continue
            properties = dict(row["entity_properties"])
            if "Asset" in row["entity_labels"]:
                risk_score = float(row.get("derived_risk_score") or 0)
                if risk_score <= 0:
                    risk_score = {
                        "critical": 90.0,
                        "high": 75.0,
                        "medium": 50.0,
                        "low": 20.0,
                    }.get(str(properties.get("criticality") or "").lower(), 0.0)
                properties["risk_score"] = risk_score
                properties["risk_level"] = self._risk_level(risk_score)
            node = self._topology_node(
                row["entity_key"], row["entity_labels"], properties
            )
            nodes[node["id"]] = node

        for row in relationship_rows:
            if not supported_labels.intersection(row["source_labels"]):
                continue
            if not supported_labels.intersection(row["target_labels"]):
                continue
            source = self._topology_node(
                row["source_key"], row["source_labels"], row["source_properties"]
            )
            target = self._topology_node(
                row["target_key"], row["target_labels"], row["target_properties"]
            )
            for node in (source, target):
                existing = nodes.get(node["id"])
                if existing:
                    existing["properties"].update(node["properties"])
                else:
                    nodes[node["id"]] = node

            relationship_id = str(row["relationship_key"])
            edges[relationship_id] = {
                "id": relationship_id,
                "source": source["id"],
                "target": target["id"],
                "type": row["relationship_type"],
                "category": self._relationship_category(row["relationship_type"]),
                "source_interface": (row.get("relationship_properties") or {}).get(
                    "source_interface"
                ),
                "target_interface": (row.get("relationship_properties") or {}).get(
                    "target_interface"
                ),
                "properties": self._json_safe(row.get("relationship_properties") or {}),
            }

        graph = {
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
            "truncated": len(node_rows) >= node_limit
            or len(relationship_rows) >= relationship_limit,
        }
        if focus_asset_id:
            return self._focus_topology(graph, focus_asset_id)
        return graph

    @staticmethod
    def _asset_from_row(row: dict) -> dict:
        asset = dict(row["asset"])
        asset["risk_score"] = row.get("risk_score")
        return Neo4jClient._json_safe(asset)

    @staticmethod
    def _vulnerability_from_row(row: dict) -> dict:
        vulnerability = dict(row["vulnerability"])
        vulnerability["asset_ids"] = [
            asset_id for asset_id in row.get("asset_ids", []) if asset_id
        ]
        return Neo4jClient._json_safe(vulnerability)

    @classmethod
    def _topology_node(cls, element_key: str, labels: list[str], properties: dict) -> dict:
        safe_properties = cls._json_safe(properties)
        entity_id = safe_properties.get("id")
        node_id = str(entity_id or element_key)
        node_type = next(
            (candidate for candidate in cls.TOPOLOGY_LABELS if candidate in labels),
            labels[0] if labels else "Entity",
        )
        label = (
            safe_properties.get("name")
            or safe_properties.get("title")
            or safe_properties.get("cve_id")
            or entity_id
            or node_type
        )
        return {
            "id": node_id,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "label": str(label),
            "type": node_type,
            "asset_type": safe_properties.get("type") if node_type == "Asset" else None,
            "risk_level": safe_properties.get("risk_level"),
            "criticality": safe_properties.get("criticality"),
            "ip_address": safe_properties.get("ip_address"),
            "properties": safe_properties,
        }

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        return "low"

    @classmethod
    def _relationship_category(cls, relationship_type: str) -> str:
        if relationship_type in cls.NETWORK_RELATIONSHIPS:
            return "network"
        if relationship_type in cls.VULNERABILITY_RELATIONSHIPS:
            return "vulnerability"
        if relationship_type in cls.RISK_RELATIONSHIPS:
            return "risk"
        if relationship_type in cls.IDENTITY_RELATIONSHIPS:
            return "identity"
        if relationship_type in {"APPLIES_TO", "PART_OF", "DEFINES"}:
            return "control"
        return "other"

    @staticmethod
    def _focus_topology(graph: dict, focus_asset_id: str) -> dict:
        focus_ids = {
            node["id"]
            for node in graph["nodes"]
            if node["id"] == focus_asset_id or node.get("entity_id") == focus_asset_id
        }
        if not focus_ids:
            return {"nodes": [], "edges": [], "truncated": graph.get("truncated", False)}

        included_ids = set(focus_ids)
        for edge in graph["edges"]:
            if edge["source"] in focus_ids or edge["target"] in focus_ids:
                included_ids.update((edge["source"], edge["target"]))

        return {
            "nodes": [node for node in graph["nodes"] if node["id"] in included_ids],
            "edges": [
                edge
                for edge in graph["edges"]
                if edge["source"] in included_ids and edge["target"] in included_ids
            ],
            "truncated": graph.get("truncated", False),
        }

    @classmethod
    def _json_safe(cls, value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._json_safe(item) for item in value]
        return str(value)


neo4j_client = Neo4jClient()
