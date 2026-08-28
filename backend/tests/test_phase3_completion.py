import pytest

from app.agents.orchestrator import _classify_intent
from app.connectors import get_connector, registered_keys
from app.connectors.base import ConfigurationError
from app.connectors.enterprise_api import _finding_status
from app.core.network_policy import TargetPolicyError, validate_connector_target
from app.graph.neo4j_client import Neo4jClient


def test_enterprise_connector_profiles_are_registered():
    keys = set(registered_keys())
    assert {
        "edr_xdr_api", "siem_api", "cmdb_api", "identity_api",
        "cloud_api", "firewall_api", "patch_api",
    } <= keys


def test_collection_target_policy_blocks_loopback():
    with pytest.raises(TargetPolicyError):
        validate_connector_target("127.0.0.1")


def test_enterprise_connector_refuses_loopback_url():
    connector = get_connector("edr_xdr_api")
    config = connector.apply_defaults({
        "base_url": "http://127.0.0.1:9000",
        "api_token": "secret",
    })
    with pytest.raises(ConfigurationError):
        connector.validate_config(config)


def test_nmap_connector_refuses_file_outside_import_root():
    connector = get_connector("nmap")
    with pytest.raises(ConfigurationError):
        connector._import_path("../outside.xml")  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("vendor_status", "expected"),
    [
        ("closed", "resolved"),
        ("risk accepted", "accepted_risk"),
        ("investigating", "in_progress"),
        ("vendor-specific-value", "open"),
    ],
)
def test_enterprise_finding_status_is_normalized(vendor_status, expected):
    assert _finding_status(vendor_status) == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("show critical CVE remediation", "risk"),
        ("check ISO 27001 controls", "compliance"),
        ("find endpoint assets", "asset"),
        ("explain our security posture", "all"),
    ],
)
def test_langgraph_orchestrator_routes_by_grounded_domain(query, expected):
    state = _classify_intent({"user_query": query})
    assert state["route"] == expected
    assert state["agent_trace"] == [f"orchestrator:{expected}"]


def test_attack_paths_are_ranked_and_normalized():
    client = Neo4jClient.__new__(Neo4jClient)
    client.run = lambda query, parameters=None: [{  # type: ignore[method-assign]
        "source_id": "asset-edge",
        "source": "EDGE-FW-01",
        "target_id": "asset-db",
        "target": "ERP-DB",
        "nodes": [],
        "relationships": ["CONNECTS_TO", "DEPENDS_ON"],
        "hops": 2,
        "vulnerabilities": [{"cvss_score": 9.8}],
        "score": 76,
    }]
    paths = client.attack_paths()
    assert paths[0]["id"] == "asset-edge->asset-db"
    assert paths[0]["risk_level"] == "critical"


def test_static_recent_runs_route_is_reachable(client, admin_headers):
    response = client.get("/api/v1/connectors/runs/recent", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_ai_runtime_status_reports_installed_models(client, admin_headers, monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "llama3.1:latest"}]}

    monkeypatch.setattr("app.api.v1.ai_models.httpx.get", lambda *args, **kwargs: Response())
    response = client.get("/api/v1/ai/models/status", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["healthy"] is True
    assert response.json()["installed_models"] == ["llama3.1:latest"]


def test_chat_endpoint_returns_langgraph_trace(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.chat.run_orchestrator",
        lambda message, user_role, conversation_history=None: {
            "final_reply": "Grounded CSOS response",
            "agent_trace": ["orchestrator:risk", "risk_assessment_agent", "chat_assistant"],
        },
    )
    response = client.post(
        "/api/v1/chat",
        headers=admin_headers,
        json={"message": "Show critical risks"},
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Grounded CSOS response"
    assert "risk_assessment_agent" in response.json()["agent_trace"]
    conversation_id = response.json()["conversation_id"]

    conversations = client.get("/api/v1/chat/conversations", headers=admin_headers)
    assert conversations.status_code == 200
    assert conversations.json()[0]["id"] == conversation_id

    messages = client.get(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=admin_headers,
    )
    assert messages.status_code == 200
    assert [item["role"] for item in messages.json()] == ["user", "assistant"]
