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
    )
    ASSET_RELATIONSHIP_TYPES = {
        "CONNECTS_TO",
        "DEPENDS_ON",
        "HOSTS",
        "COMMUNICATES_WITH",
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
            OPTIONAL MATCH (a)-[:HAS_VULNERABILITY]->(v:Vulnerability)
            WITH a, max(CASE WHEN v.status IN ['resolved','closed','accepted','mitigated','false_positive'] THEN 0
                       ELSE coalesce(toFloat(v.cvss_score), CASE v.severity WHEN 'critical' THEN 10 WHEN 'high' THEN 8 WHEN 'medium' THEN 5 WHEN 'low' THEN 2 ELSE 0 END) END) AS severity
            RETURN properties(a) AS asset,
              round(severity * 10 * CASE a.criticality WHEN 'critical' THEN 1.0 WHEN 'high' THEN 0.8 WHEN 'low' THEN 0.4 ELSE 0.6 END
                * CASE a.exposure WHEN 'internet' THEN 1.0 WHEN 'partner' THEN 0.8 ELSE 0.6 END, 1) AS risk_score
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
            OPTIONAL MATCH (a)-[:HAS_VULNERABILITY]->(v:Vulnerability)
            WITH a, max(CASE WHEN v.status IN ['resolved','closed','accepted','mitigated','false_positive'] THEN 0
                       ELSE coalesce(toFloat(v.cvss_score), CASE v.severity WHEN 'critical' THEN 10 WHEN 'high' THEN 8 WHEN 'medium' THEN 5 WHEN 'low' THEN 2 ELSE 0 END) END) AS severity
            RETURN properties(a) AS asset,
              round(severity * 10 * CASE a.criticality WHEN 'critical' THEN 1.0 WHEN 'high' THEN 0.8 WHEN 'low' THEN 0.4 ELSE 0.6 END
                * CASE a.exposure WHEN 'internet' THEN 1.0 WHEN 'partner' THEN 0.8 ELSE 0.6 END, 1) AS risk_score
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
            OPTIONAL MATCH (a)-[:HAS_VULNERABILITY]->(v:Vulnerability)
            WITH a, max(CASE WHEN v.status IN ['resolved','closed','accepted','mitigated','false_positive'] THEN 0
                       ELSE coalesce(toFloat(v.cvss_score), CASE v.severity WHEN 'critical' THEN 10 WHEN 'high' THEN 8 WHEN 'medium' THEN 5 WHEN 'low' THEN 2 ELSE 0 END) END) AS severity
            RETURN properties(a) AS asset,
              round(severity * 10 * CASE a.criticality WHEN 'critical' THEN 1.0 WHEN 'high' THEN 0.8 WHEN 'low' THEN 0.4 ELSE 0.6 END
                * CASE a.exposure WHEN 'internet' THEN 1.0 WHEN 'partner' THEN 0.8 ELSE 0.6 END, 1) AS risk_score
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
        focus_asset_id: str | None = None,
    ) -> dict:
        node_limit = min(relationship_limit * 2, 4000)
        node_rows = self.run(
            """
        MATCH (entity)
        RETURN elementId(entity) AS entity_key,
               labels(entity) AS entity_labels,
               properties(entity) AS entity_properties
        LIMIT $limit
        """,
            {"limit": node_limit},
        )
        relationship_rows = self.run(
            """
        MATCH (source)-[relationship]->(target)
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
            {"limit": relationship_limit},
        )

        nodes: dict[str, dict] = {}
        edges: dict[str, dict] = {}
        supported_labels = set(self.TOPOLOGY_LABELS)

        # Load supported entities independently so a newly seeded or imported
        # node remains visible even before relationships have been created.
        for row in node_rows:
            if not supported_labels.intersection(row["entity_labels"]):
                continue
            node = self._topology_node(
                row["entity_key"], row["entity_labels"], row["entity_properties"]
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
                "properties": self._json_safe(row.get("relationship_properties") or {}),
            }

        graph = {"nodes": list(nodes.values()), "edges": list(edges.values())}
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
            "properties": safe_properties,
        }

    @staticmethod
    def _focus_topology(graph: dict, focus_asset_id: str) -> dict:
        focus_ids = {
            node["id"]
            for node in graph["nodes"]
            if node["id"] == focus_asset_id or node.get("entity_id") == focus_asset_id
        }
        if not focus_ids:
            return {"nodes": [], "edges": []}

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
