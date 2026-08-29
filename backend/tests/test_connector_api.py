"""Portal/API checks for source administration and write-only ingestion."""
from __future__ import annotations


def _ssh_source():
    return {
        "name": "Branch routers",
        "connector_key": "ssh_network",
        "config": {
            "hosts": "172.16.40.1", "device_type": "cisco_ios",
            "username": "netops", "password": "do-not-return-this",
        },
        "schedule_minutes": 30,
    }


def test_catalogue_requires_login_and_describes_secret_fields(client, admin_headers):
    assert client.get("/api/v1/connectors/types").status_code == 401
    response = client.get("/api/v1/connectors/types", headers=admin_headers)
    assert response.status_code == 200
    ssh = next(item for item in response.json() if item["key"] == "ssh_network")
    fields = {field["name"]: field for field in ssh["config_fields"]}
    assert fields["password"]["secret"] is True
    assert fields["device_type"]["choices"]


def test_source_lifecycle_redacts_and_preserves_credentials(client, admin_headers, db_session):
    created = client.post("/api/v1/connectors", json=_ssh_source(), headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["config"]["password"] == "••••••••"
    assert "do-not-return-this" not in client.get("/api/v1/connectors", headers=admin_headers).text

    source_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/connectors/{source_id}",
        json={"name": "Branch network", "config": {**_ssh_source()["config"], "password": "••••••••"}},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    from app.core.secrets import decrypt_config
    from app.models.connector import ConnectorConfig
    record = db_session.query(ConnectorConfig).first()
    assert decrypt_config(record.config, {"password", "enable_secret"})["password"] == "do-not-return-this"

    assert client.get(f"/api/v1/connectors/{source_id}/runs", headers=admin_headers).json() == []
    assert client.delete(f"/api/v1/connectors/{source_id}", headers=admin_headers).status_code == 204


def test_invalid_or_unschedulable_sources_are_rejected(client, admin_headers):
    unknown = client.post("/api/v1/connectors", json={"name": "Unknown", "connector_key": "not-real"}, headers=admin_headers)
    assert unknown.status_code == 400
    incomplete = client.post("/api/v1/connectors", json={"name": "Incomplete", "connector_key": "ssh_network", "config": {"hosts": "172.16.1.1"}}, headers=admin_headers)
    assert incomplete.status_code == 422
    push = client.post("/api/v1/connectors", json={"name": "Log receiver", "connector_key": "syslog", "schedule_minutes": 15}, headers=admin_headers)
    assert push.status_code == 422


def _issue_key(client, admin_headers, scope):
    response = client.post("/api/v1/ingest/keys", json={"name": f"{scope} source", "scope": scope}, headers=admin_headers)
    assert response.status_code == 201
    return response.json()


def test_ingestion_key_is_shown_once_and_can_be_revoked(client, admin_headers):
    issued = _issue_key(client, admin_headers, "agent")
    assert issued["api_key"].startswith("csos_")
    listed = client.get("/api/v1/ingest/keys", headers=admin_headers)
    assert issued["api_key"] not in listed.text
    assert client.delete(f"/api/v1/ingest/keys/{issued['id']}", headers=admin_headers).status_code == 204
    assert client.get("/api/v1/ingest/keys", headers=admin_headers).json()[0]["enabled"] is False


def test_endpoint_ingestion_requires_correct_scope_and_records_use(client, admin_headers, monkeypatch):
    issued = _issue_key(client, admin_headers, "agent")
    report = {
        "agent_id": "agent-finance-4", "hostname": "finance-app-04",
        "network": {"interfaces": [{"name": "eth0", "ip_address": "172.16.60.24"}]},
        "listening_ports": [{"port": 23, "address": "0.0.0.0"}],
    }
    assert client.post("/api/v1/ingest/agent", json=report).status_code == 401
    monkeypatch.setattr("app.services.collection.network_writer.write", lambda result: {"assets": len(result.assets), "vulnerabilities": len(result.vulnerabilities)})
    response = client.post("/api/v1/ingest/agent", json=report, headers={"X-API-Key": issued["api_key"]})
    assert response.status_code == 200
    assert response.json()["written"] == {"assets": 1, "vulnerabilities": 1}
    assert client.get("/api/v1/ingest/keys", headers=admin_headers).json()[0]["use_count"] == 1


def test_http_syslog_ingestion_normalizes_a_batch(client, admin_headers, monkeypatch):
    issued = _issue_key(client, admin_headers, "syslog")
    observed = {}
    def capture(result):
        observed.update({"assets": len(result.assets), "events": len(result.events)})
        return observed
    monkeypatch.setattr("app.services.collection.network_writer.write", capture)
    response = client.post(
        "/api/v1/ingest/syslog",
        json={"source_ip": "172.16.50.2", "lines": ["<34>Nov 02 08:10:01 access-02 interface down", "<13>Nov 02 08:10:02 access-02 config saved"]},
        headers={"X-API-Key": issued["api_key"]},
    )
    assert response.status_code == 200
    assert observed == {"assets": 1, "events": 2}
