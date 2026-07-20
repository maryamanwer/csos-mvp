"""
LangChain tools the Compliance Agent can call.
TODO(M3): wrap with @tool decorator.
"""
from app.graph.neo4j_client import neo4j_client


def get_framework_coverage(framework_name: str) -> list[dict]:
    """Return controls belonging to a framework, for coverage calculation."""
    query = """
    MATCH (c:Control)-[:PART_OF]->(f:Framework {name: $name})
    RETURN c
    """
    return neo4j_client.run(query, {"name": framework_name})


def list_control_gaps(framework_name: str) -> list[dict]:
    """Return controls in a framework that are not yet APPLIES_TO any asset."""
    query = """
    MATCH (c:Control)-[:PART_OF]->(f:Framework {name: $name})
    WHERE NOT (c)-[:APPLIES_TO]->(:Asset)
    RETURN c
    """
    return neo4j_client.run(query, {"name": framework_name})
