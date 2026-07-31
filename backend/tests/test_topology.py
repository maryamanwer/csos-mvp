from app.graph.neo4j_client import Neo4jClient


ROWS = [
    {
        "source_key": "neo4j-1",
        "source_labels": ["Asset"],
        "source_properties": {
            "id": "asset-001",
            "name": "ERP-PROD-DB01",
            "created_at": object(),
        },
        "target_key": "neo4j-2",
        "target_labels": ["Identity"],
        "target_properties": {"id": "identity-001", "name": "svc-erp-db"},
        "relationship_key": "relationship-1",
        "relationship_type": "OWNED_BY",
        "relationship_properties": {},
    },
    {
        "source_key": "neo4j-3",
        "source_labels": ["Risk"],
        "source_properties": {"id": "risk-001", "title": "Data exposure"},
        "target_key": "neo4j-1",
        "target_labels": ["Asset"],
        "target_properties": {"id": "asset-001", "name": "ERP-PROD-DB01"},
        "relationship_key": "relationship-2",
        "relationship_type": "AFFECTS",
        "relationship_properties": {"confidence": 0.9},
    },
]


def topology_client() -> Neo4jClient:
    client = Neo4jClient.__new__(Neo4jClient)
    client.run = lambda query, parameters=None: ROWS  # type: ignore[method-assign]
    return client


def test_topology_projection_normalizes_nodes_and_edges():
    graph = topology_client().get_topology()

    assert {node["id"] for node in graph["nodes"]} == {
        "asset-001",
        "identity-001",
        "risk-001",
    }
    assert {edge["type"] for edge in graph["edges"]} == {"OWNED_BY", "AFFECTS"}
    asset = next(node for node in graph["nodes"] if node["id"] == "asset-001")
    assert asset["label"] == "ERP-PROD-DB01"
    assert isinstance(asset["properties"]["created_at"], str)


def test_topology_projection_can_focus_an_asset_neighborhood():
    graph = topology_client().get_topology(focus_asset_id="asset-001")

    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2


def test_topology_projection_returns_empty_for_unknown_focus():
    graph = topology_client().get_topology(focus_asset_id="asset-missing")

    assert graph == {"nodes": [], "edges": []}
