"""
Thin wrapper around the Neo4j driver, used by services and AI agent tools
to run Cypher queries against the Cyber Knowledge Graph.

TODO(M3): add connection pooling config, retry policy, and query result
caching for hot paths (e.g. top-risks).
"""
from neo4j import GraphDatabase

from app.core.config import settings


class Neo4jClient:
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

    # ---- Example convenience methods (extend in M3) ----
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


neo4j_client = Neo4jClient()
