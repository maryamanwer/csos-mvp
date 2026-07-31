"""
LangChain tools the Asset Intelligence Agent can call.
TODO(P3): wrap with @tool decorator and register on the agent's tool list.
"""
from app.graph.neo4j_client import neo4j_client


def get_asset(asset_id: str) -> dict | None:
    """Fetch a single asset by id, including basic properties."""
    return neo4j_client.get_asset(asset_id)


def search_assets(name_contains: str, limit: int = 10) -> list[dict]:
    """Search assets by partial name match."""
    query = "MATCH (a:Asset) WHERE toLower(a.name) CONTAINS toLower($q) RETURN a LIMIT $limit"
    return neo4j_client.run(query, {"q": name_contains, "limit": limit})


def get_asset_relationships(asset_id: str) -> list[dict]:
    """Return the full relationship neighborhood for an asset."""
    query = "MATCH (a:Asset {id: $id})-[rel]-(n) RETURN type(rel) AS relationship, n"
    return neo4j_client.run(query, {"id": asset_id})
