from app.core.config import settings


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.3.0"


def test_database_login_current_user_and_refresh_rotation(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.DEMO_ADMIN_EMAIL,
            "password": settings.DEMO_ADMIN_PASSWORD,
        },
    )

    assert login_response.status_code == 200
    tokens = login_response.json()
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "Admin"

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["refresh_token"] != tokens["refresh_token"]

    replay_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay_response.status_code == 401


def test_database_login_rejects_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.DEMO_ADMIN_EMAIL, "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_admin_user_crud_and_audit_log(client, admin_headers):
    create_response = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "email": "analyst@csos.com",
            "password": "analyst-pass",
            "full_name": "Security Analyst",
            "role": "Analyst",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=admin_headers,
        json={"role": "Engineer"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "Engineer"

    list_response = client.get("/api/v1/admin/users", headers=admin_headers)
    assert list_response.status_code == 200
    assert any(user["email"] == "analyst@csos.com" for user in list_response.json())

    roles_response = client.get("/api/v1/admin/roles", headers=admin_headers)
    assert roles_response.status_code == 200
    analyst_role = next(role for role in roles_response.json() if role["name"] == "Analyst")
    role_update_response = client.put(
        f"/api/v1/admin/roles/{analyst_role['id']}",
        headers=admin_headers,
        json={"permission_codes": ["dashboard:read", "asset:read"]},
    )
    assert role_update_response.status_code == 200
    assert role_update_response.json()["permission_codes"] == [
        "asset:read",
        "dashboard:read",
    ]

    audit_response = client.get("/api/v1/admin/audit-log", headers=admin_headers)
    assert audit_response.status_code == 200
    assert {entry["action"] for entry in audit_response.json()} >= {
        "USER_CREATED",
        "USER_UPDATED",
        "ROLE_UPDATED",
    }


def test_asset_crud_endpoints_delegate_to_neo4j(client, admin_headers, monkeypatch):
    asset = {
        "id": "asset-test",
        "name": "TEST-SERVER",
        "type": "server",
        "environment": "test",
        "criticality": "medium",
        "owner": "QA",
        "risk_score": 0,
    }
    monkeypatch.setattr(
        "app.api.v1.assets.neo4j_client.create_asset",
        lambda properties: {**asset, **properties},
    )
    monkeypatch.setattr(
        "app.api.v1.assets.neo4j_client.list_assets",
        lambda **kwargs: [asset],
    )

    create_response = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={
            "name": "TEST-SERVER",
            "type": "server",
            "environment": "test",
            "criticality": "medium",
            "owner": "QA",
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["id"] == "asset-test"

    list_response = client.get("/api/v1/assets", headers=admin_headers)
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "TEST-SERVER"


def test_dashboard_endpoint_returns_live_summary(client, admin_headers, monkeypatch):
    summary = {
        "overall_risk_score": 78,
        "asset_count": 5,
        "open_vulnerability_count": 3,
        "compliance_pct": 66.7,
        "asset_criticality": [{"label": "critical", "value": 2}],
        "vulnerability_severity": [{"label": "high", "value": 2}],
        "compliance_frameworks": [],
        "top_risks": [],
    }
    monkeypatch.setattr(
        "app.api.v1.dashboard.neo4j_client.executive_summary",
        lambda: summary,
    )

    response = client.get("/api/v1/dashboard/executive", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["asset_count"] == 5


def test_topology_endpoint_returns_graph(client, admin_headers, monkeypatch):
    expected = {
        "nodes": [
            {
                "id": "asset-001",
                "entity_id": "asset-001",
                "label": "ERP-PROD-DB01",
                "type": "Asset",
                "asset_type": "database",
                "risk_level": "high",
                "criticality": "critical",
                "ip_address": "10.20.30.20",
                "properties": {"id": "asset-001", "name": "ERP-PROD-DB01"},
            }
        ],
        "edges": [],
        "truncated": False,
    }
    monkeypatch.setattr(
        "app.api.v1.topology.neo4j_client.get_topology",
        lambda relationship_limit, node_limit, focus_asset_id: expected,
    )

    response = client.get("/api/v1/topology", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == expected


def test_topology_endpoint_requires_authentication(client):
    response = client.get("/api/v1/topology")

    assert response.status_code == 401


def test_security_findings_endpoint_returns_correlated_page(client, admin_headers, monkeypatch):
    finding = {
        "finding_id": "vuln-001",
        "cve_id": "CVE-2026-4102",
        "title": "Internet-facing web service remote execution",
        "asset_id": "asset-007",
        "asset_name": "WEB-PROD-01",
        "preferred_hostname": "web-prod-01.csos.demo",
        "asset_type": "server",
        "asset_criticality": "high",
        "asset_owner": "Digital Services",
        "ip_address": "10.20.10.11",
        "operating_system": "Ubuntu Server 24.04",
        "edr_status": "active",
        "edr_product": "CSOS Endpoint Sensor",
        "severity": "critical",
        "cvss_score": 9.8,
        "risk_score": 96,
        "risk_level": "high",
        "status": "open",
        "first_detected": "2026-08-01T03:45:00Z",
        "last_seen": "2026-08-09T02:10:00Z",
        "sla_due_at": "2026-08-08T00:00:00Z",
        "sla_status": "breached",
        "sla_days_remaining": -1,
        "data_sources": ["Vulnerability Management", "EDR / XDR"],
        "recommended_remediation": "Apply the vendor security update.",
        "controls": [],
    }
    summary = {
        "total_findings": 1,
        "critical_findings": 1,
        "sla_breaches": 1,
        "critical_assets_without_edr": 0,
        "critical_vulnerabilities_on_critical_assets": 1,
        "outdated_security_agents": 0,
        "assets_missing_controls": 0,
        "unmanaged_assets": 0,
    }
    captured = {}

    def fake_findings(**kwargs):
        captured.update(kwargs)
        return {"items": [finding], "total": 1}

    monkeypatch.setattr(
        "app.api.v1.findings.neo4j_client.list_security_findings",
        fake_findings,
    )
    monkeypatch.setattr(
        "app.api.v1.findings.neo4j_client.findings_summary",
        lambda: summary,
    )

    response = client.get(
        "/api/v1/findings?risk_level=high&status=open",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["asset_name"] == "WEB-PROD-01"
    assert response.json()["summary"]["sla_breaches"] == 1
    assert captured["risk_level"] == "high"
    assert captured["status"] == "open"

    export_response = client.get(
        "/api/v1/findings/export?risk_level=high&sort_by=first_detected&sort_direction=asc",
        headers=admin_headers,
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "CVE-2026-4102" in export_response.text
    assert captured["sort_by"] == "first_detected"
    assert captured["sort_direction"] == "asc"


def test_security_findings_endpoint_requires_authentication(client):
    response = client.get("/api/v1/findings")

    assert response.status_code == 401
