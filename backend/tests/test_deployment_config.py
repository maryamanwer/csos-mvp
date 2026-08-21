from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_compose_wires_graph_initialization_and_web_proxy_port():
    compose = yaml.safe_load((REPOSITORY_ROOT / "docker-compose.yml").read_text())
    services = compose["services"]

    assert services["frontend"]["ports"] == ["3000:80"]
    assert services["backend"]["depends_on"]["neo4j-init"]["condition"] == "service_completed_successfully"
    assert services["neo4j-init"]["volumes"] == [
        "./database/neo4j/schema.cypher:/schema/schema.cypher:ro"
    ]
    assert services["mcp-gateway"]["ports"] == ["8001:8001"]
    assert services["mcp-gateway"]["depends_on"]["backend"]["condition"] == "service_healthy"
    assert services["frontend"]["depends_on"]["mcp-gateway"]["condition"] == "service_healthy"


def test_nginx_proxies_api_and_supports_client_side_routes():
    nginx_config = (REPOSITORY_ROOT / "frontend" / "nginx.conf").read_text()

    assert "proxy_pass http://backend:8000;" in nginx_config
    assert "try_files $uri $uri/ /index.html;" in nginx_config
