from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app


client = TestClient(app)


def authorization_header(role: str = "Admin") -> dict[str, str]:
    token = create_access_token("tester@csos.local", role)
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_development_login_and_current_user():
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.DEMO_ADMIN_EMAIL,
            "password": settings.DEMO_ADMIN_PASSWORD,
        },
    )

    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "Admin"


def test_development_login_rejects_wrong_password():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.DEMO_ADMIN_EMAIL, "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_topology_endpoint_returns_graph(monkeypatch):
    expected = {
        "nodes": [
            {
                "id": "asset-001",
                "entity_id": "asset-001",
                "label": "ERP-PROD-DB01",
                "type": "Asset",
                "properties": {"id": "asset-001", "name": "ERP-PROD-DB01"},
            }
        ],
        "edges": [],
    }
    monkeypatch.setattr(
        "app.api.v1.topology.neo4j_client.get_topology",
        lambda relationship_limit, focus_asset_id: expected,
    )

    response = client.get("/api/v1/topology", headers=authorization_header())

    assert response.status_code == 200
    assert response.json() == expected


def test_topology_endpoint_requires_authentication():
    response = client.get("/api/v1/topology")

    assert response.status_code == 401
