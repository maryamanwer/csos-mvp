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

NODE_ROWS = [
    {
        "entity_key": "neo4j-1",
        "entity_labels": ["Asset"],
        "entity_properties": {
            "id": "asset-001",
            "name": "ERP-PROD-DB01",
            "created_at": object(),
        },
        "derived_risk_score": 82,
    },
    {
        "entity_key": "neo4j-2",
        "entity_labels": ["Identity"],
        "entity_properties": {"id": "identity-001", "name": "svc-erp-db"},
    },
    {
        "entity_key": "neo4j-3",
        "entity_labels": ["Risk"],
        "entity_properties": {"id": "risk-001", "title": "Data exposure"},
    },
    {
        "entity_key": "neo4j-4",
        "entity_labels": ["Control"],
        "entity_properties": {"id": "control-001", "name": "TLS baseline"},
    },
]


def topology_client() -> Neo4jClient:
    client = Neo4jClient.__new__(Neo4jClient)

    def run(query, parameters=None):
        return NODE_ROWS if "MATCH (entity)" in query else ROWS

    client.run = run  # type: ignore[method-assign]
    return client


def test_topology_projection_normalizes_nodes_and_edges():
    graph = topology_client().get_topology()

    assert {node["id"] for node in graph["nodes"]} == {
        "asset-001",
        "identity-001",
        "risk-001",
        "control-001",
    }
    assert {edge["type"] for edge in graph["edges"]} == {"OWNED_BY", "AFFECTS"}
    asset = next(node for node in graph["nodes"] if node["id"] == "asset-001")
    assert asset["label"] == "ERP-PROD-DB01"
    assert asset["risk_level"] == "high"
    assert isinstance(asset["properties"]["created_at"], str)
    assert {edge["category"] for edge in graph["edges"]} == {"identity", "risk"}


def test_topology_projection_includes_entities_without_relationships():
    graph = topology_client().get_topology()

    control = next(node for node in graph["nodes"] if node["id"] == "control-001")
    assert control["label"] == "TLS baseline"
    assert not any(
        edge["source"] == "control-001" or edge["target"] == "control-001"
        for edge in graph["edges"]
    )


def test_topology_projection_can_focus_an_asset_neighborhood():
    graph = topology_client().get_topology(focus_asset_id="asset-001")

    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2


def test_topology_projection_returns_empty_for_unknown_focus():
    graph = topology_client().get_topology(focus_asset_id="asset-missing")

    assert graph == {"nodes": [], "edges": [], "truncated": False}


def test_topology_uses_asset_criticality_when_linked_risk_is_missing():
    client = Neo4jClient.__new__(Neo4jClient)
    node_rows = [
        {
            "entity_key": "neo4j-critical",
            "entity_labels": ["Asset"],
            "entity_properties": {
                "id": "asset-critical",
                "name": "PAYMENTS-DB",
                "criticality": "critical",
            },
            "derived_risk_score": 0,
        }
    ]

    def run(query, parameters=None):
        return node_rows if "MATCH (entity)" in query else []

    client.run = run  # type: ignore[method-assign]
    graph = client.get_topology()
    asset = graph["nodes"][0]

    assert asset["risk_level"] == "high"
    assert asset["properties"]["risk_score"] == 90.0
