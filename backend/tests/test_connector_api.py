"""HTTP-level tests for the collection layer.

These run against the real FastAPI app with a SQLite database, so they cover
authentication, role enforcement, validation and — most importantly — that a
stored credential never comes back out of the API.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def ssh_config_payload():
    return {
        "name": "سويتشات النواة",
        "connector_key": "ssh_network",
        "description": "أجهزة الشبكة الأساسية في مركز البيانات",
        "config": {
            "hosts": "10.0.10.1\n10.0.10.2",
            "device_type": "cisco_ios",
            "username": "netadmin",
            "password": "S3cretPassw0rd",
        },
        "schedule_minutes": 60,
    }


class TestConnectorTypes:
    def test_lists_available_connectors(self, client, admin_headers):
        response = client.get("/api/v1/connectors/types", headers=admin_headers)
        assert response.status_code == 200

        keys = {item["key"] for item in response.json()}
        assert {"ssh_network", "snmp", "syslog", "agent", "nmap"} <= keys

    def test_describes_configuration_fields_for_the_ui(self, client, admin_headers):
        """The UI builds forms from this, so the contract must hold."""
        response = client.get("/api/v1/connectors/types", headers=admin_headers)
        ssh = next(i for i in response.json() if i["key"] == "ssh_network")

        fields = {field["name"]: field for field in ssh["config_fields"]}
        assert fields["password"]["secret"] is True
        assert fields["username"]["secret"] is False
        assert fields["device_type"]["choices"]

    def test_requires_authentication(self, client):
        assert client.get("/api/v1/connectors/types").status_code == 401


class TestConnectorConfigLifecycle:
    def test_create_then_list(self, client, admin_headers, ssh_config_payload):
        created = client.post(
            "/api/v1/connectors", json=ssh_config_payload, headers=admin_headers
        )
        assert created.status_code == 201
        assert created.json()["name"] == "سويتشات النواة"

        listed = client.get("/api/v1/connectors", headers=admin_headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

    def test_password_is_never_returned(
        self, client, admin_headers, ssh_config_payload
    ):
        """The stored credential must not leak back through any read path."""
        created = client.post(
            "/api/v1/connectors", json=ssh_config_payload, headers=admin_headers
        )
        body = created.json()
        assert body["config"]["password"] == "••••••••"
        assert body["config"]["username"] == "netadmin"

        listed = client.get("/api/v1/connectors", headers=admin_headers)
        assert "S3cretPassw0rd" not in listed.text

    def test_defaults_are_applied(self, client, admin_headers, ssh_config_payload):
        created = client.post(
            "/api/v1/connectors", json=ssh_config_payload, headers=admin_headers
        )
        assert created.json()["config"]["port"] == 22

    def test_unknown_connector_is_rejected(self, client, admin_headers):
        response = client.post(
            "/api/v1/connectors",
            json={"name": "خطأ", "connector_key": "nope", "config": {}},
            headers=admin_headers,
        )
        assert response.status_code == 400

    def test_incomplete_config_is_rejected(self, client, admin_headers):
        response = client.post(
            "/api/v1/connectors",
            json={
                "name": "ناقص",
                "connector_key": "ssh_network",
                "config": {"hosts": "10.0.0.1"},
            },
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_push_connector_cannot_be_scheduled(self, client, admin_headers):
        """Scheduling a listener is meaningless and must be refused."""
        response = client.post(
            "/api/v1/connectors",
            json={
                "name": "سجلات",
                "connector_key": "syslog",
                "config": {},
                "schedule_minutes": 30,
            },
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_update_keeps_secret_when_mask_is_sent_back(
        self, client, admin_headers, ssh_config_payload, db_session
    ):
        """Editing a form must not overwrite the password with the mask."""
        created = client.post(
            "/api/v1/connectors", json=ssh_config_payload, headers=admin_headers
        ).json()

        updated = client.patch(
            f"/api/v1/connectors/{created['id']}",
            json={
                "name": "سويتشات النواة — محدّث",
                "config": {
                    "hosts": "10.0.10.1",
                    "device_type": "cisco_ios",
                    "username": "netadmin",
                    "password": "••••••••",
                },
            },
            headers=admin_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "سويتشات النواة — محدّث"

        # Prove the original credential survived, by reading it back from the
        # same session the API wrote through.
        from app.core.secrets import decrypt_config
        from app.models.connector import ConnectorConfig

        stored = db_session.query(ConnectorConfig).first()
        plain = decrypt_config(stored.config, {"password", "enable_secret"})
        assert plain["password"] == "S3cretPassw0rd"

    def test_delete(self, client, admin_headers, ssh_config_payload):
        created = client.post(
            "/api/v1/connectors", json=ssh_config_payload, headers=admin_headers
        ).json()

        assert (
            client.delete(
                f"/api/v1/connectors/{created['id']}", headers=admin_headers
            ).status_code
            == 204
        )
        assert client.get("/api/v1/connectors", headers=admin_headers).json() == []

    def test_run_history_is_empty_before_any_run(
        self, client, admin_headers, ssh_config_payload
    ):
        created = client.post(
            "/api/v1/connectors", json=ssh_config_payload, headers=admin_headers
        ).json()
        response = client.get(
            f"/api/v1/connectors/{created['id']}/runs", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_missing_connector_is_404(self, client, admin_headers):
        response = client.get(
            "/api/v1/connectors/00000000-0000-0000-0000-000000000000/runs",
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestIngestApiKeys:
    def test_key_is_shown_once_and_never_again(self, client, admin_headers):
        created = client.post(
            "/api/v1/ingest/keys",
            json={"name": "وكلاء الخوادم", "scope": "agent"},
            headers=admin_headers,
        )
        assert created.status_code == 201
        plaintext = created.json()["api_key"]
        assert plaintext.startswith("csos_")

        listed = client.get("/api/v1/ingest/keys", headers=admin_headers)
        assert plaintext not in listed.text
        assert listed.json()[0]["key_prefix"] == plaintext[:12]

    def test_revoked_key_is_disabled_not_deleted(self, client, admin_headers):
        created = client.post(
            "/api/v1/ingest/keys",
            json={"name": "مؤقت", "scope": "agent"},
            headers=admin_headers,
        ).json()

        assert (
            client.delete(
                f"/api/v1/ingest/keys/{created['id']}", headers=admin_headers
            ).status_code
            == 204
        )
        keys = client.get("/api/v1/ingest/keys", headers=admin_headers).json()
        assert len(keys) == 1  # audit trail preserved
        assert keys[0]["enabled"] is False


class TestAgentIngestEndpoint:
    @pytest.fixture()
    def api_key(self, client, admin_headers):
        return client.post(
            "/api/v1/ingest/keys",
            json={"name": "وكلاء", "scope": "agent"},
            headers=admin_headers,
        ).json()["api_key"]

    @pytest.fixture()
    def report(self):
        return {
            "agent_id": "agent-77",
            "hostname": "web-01",
            "system": {"os_name": "Linux", "os_version": "Ubuntu 24.04"},
            "network": {"interfaces": [{"name": "eth0", "ip_address": "10.0.50.10"}]},
            "listening_ports": [{"port": 23, "address": "0.0.0.0"}],
        }

    def test_rejects_missing_key(self, client, report):
        assert client.post("/api/v1/ingest/agent", json=report).status_code == 401

    def test_rejects_invalid_key(self, client, report):
        response = client.post(
            "/api/v1/ingest/agent",
            json=report,
            headers={"X-API-Key": "csos_totally_wrong"},
        )
        assert response.status_code == 401
    def test_rejects_revoked_key(self, client, admin_headers, report):
        created = client.post(
            "/api/v1/ingest/keys",
            json={"name": "ملغى", "scope": "agent"},
            headers=admin_headers,
        ).json()
        client.delete(
            f"/api/v1/ingest/keys/{created['id']}", headers=admin_headers
        )
        response = client.post(
            "/api/v1/ingest/agent",
            json=report,
            headers={"X-API-Key": created["api_key"]},
        )
        assert response.status_code == 401

    def test_accepts_valid_report(self, client, api_key, report, monkeypatch):
        written = {}

        def fake_write(result):
            written["result"] = result
            return {"assets": len(result.assets), "vulnerabilities": len(result.vulnerabilities)}

        monkeypatch.setattr(
            "app.services.collection.network_writer.write", fake_write
        )

        response = client.post(
            "/api/v1/ingest/agent", json=report, headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        assert response.json()["accepted"] is True
        assert response.json()["written"]["assets"] == 1
        # Telnet on an endpoint must surface as a finding.
        assert response.json()["written"]["vulnerabilities"] == 1

    def test_key_usage_is_recorded(self, client, admin_headers, api_key, report, monkeypatch):
        monkeypatch.setattr(
            "app.services.collection.network_writer.write", lambda result: {}
        )
        client.post(
            "/api/v1/ingest/agent", json=report, headers={"X-API-Key": api_key}
        )
        keys = client.get("/api/v1/ingest/keys", headers=admin_headers).json()
        assert keys[0]["use_count"] == 1
        assert keys[0]["last_used_at"]

    def test_malformed_report_is_422(self, client, api_key):
        response = client.post(
            "/api/v1/ingest/agent",
            json={"hostname": "no-agent-id"},
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 422


class TestSyslogIngestEndpoint:
    @pytest.fixture()
    def api_key(self, client, admin_headers):
        return client.post(
            "/api/v1/ingest/keys",
            json={"name": "موجّه السجلات", "scope": "syslog"},
            headers=admin_headers,
        ).json()["api_key"]

    def test_accepts_a_batch(self, client, api_key, monkeypatch):
        captured = {}

        def fake_write(result):
            captured["events"] = len(result.events)
            captured["assets"] = len(result.assets)
            return {"events": len(result.events)}

        monkeypatch.setattr(
            "app.services.collection.network_writer.write", fake_write
        )

        response = client.post(
            "/api/v1/ingest/syslog",
            json={
                "lines": [
                    "<34>Oct 11 22:14:15 core-sw-01 %LINK-3-UPDOWN: Gi0/1 down",
                    "<13>Oct 11 22:14:16 core-sw-01 config changed",
                ],
                "source_ip": "10.0.10.1",
            },
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        assert captured["events"] == 2
        assert captured["assets"] == 1  # both lines came from one device

    def test_requires_a_key(self, client):
        response = client.post("/api/v1/ingest/syslog", json={"lines": ["test"]})
        assert response.status_code == 401
