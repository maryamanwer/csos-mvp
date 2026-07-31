"""
Thin wrapper around the Neo4j driver, used by services and AI agent tools
to run Cypher queries against the Cyber Knowledge Graph.

TODO(P3): add connection pooling config, retry policy, and query result
caching for hot paths (e.g. top-risks).
"""
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

    def __init__(self):
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self._driver.close()

    def run(self, query: str, parameters: dict | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    # ---- Example convenience methods (extend in Phase 3) ----
    def get_asset(self, asset_id: str) -> dict | None:
        rows = self.run("MATCH (a:Asset {id: $id}) RETURN a", {"id": asset_id})
        return rows[0]["a"] if rows else None

    def top_risks(self, limit: int = 5) -> list[dict]:
        query = """
        MATCH (r:Risk)-[:AFFECTS]->(a:Asset)
        OPTIONAL MATCH (c:Control)-[:MITIGATES]->(r)
        RETURN r, a, collect(c) AS controls
        ORDER BY r.score DESC LIMIT $limit
        """
        return self.run(query, {"limit": limit})

    def get_topology(
        self,
        relationship_limit: int = 500,
        focus_asset_id: str | None = None,
    ) -> dict:
        """Return a UI-ready graph projection from stored Neo4j relationships."""
        query = """
        MATCH (source)-[relationship]->(target)
        WHERE any(label IN labels(source) WHERE label IN $labels)
          AND any(label IN labels(target) WHERE label IN $labels)
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
        """
        rows = self.run(
            query,
            {"labels": list(self.TOPOLOGY_LABELS), "limit": relationship_limit},
        )

        nodes: dict[str, dict] = {}
        edges: dict[str, dict] = {}
        for row in rows:
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
