"""
LangChain tools the Risk Assessment Agent can call.
TODO(M3): wrap with @tool decorator.
"""
from app.graph.neo4j_client import neo4j_client


def list_top_risks(limit: int = 5) -> list[dict]:
    """Return the highest-scored open risks with affected asset and controls."""
    return neo4j_client.top_risks(limit=limit)


def get_vulnerabilities_for_asset(asset_id: str) -> list[dict]:
    """Return vulnerabilities linked to a specific asset."""
    query = """
    MATCH (a:Asset {id: $id})-[:HAS_VULNERABILITY]->(v:Vulnerability)
    RETURN v ORDER BY v.cvss_score DESC
    """
    return neo4j_client.run(query, {"id": asset_id})
