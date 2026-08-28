# CSOS MCP Gateway

## Delivered capability

CSOS now includes a standalone Model Context Protocol resource server at
`http://localhost:8001/mcp`. It uses the official Python MCP SDK and the
Streamable HTTP transport. The service is separate from the existing FastAPI
runtime so that MCP SDK upgrades do not change the platform's pinned API and AI
dependencies.

The gateway accepts the same signed access JWT issued by CSOS login. The token
contains both platform and MCP audiences. The gateway validates its signature,
issuer, audience, expiry, token type, subject, and role before an MCP request is
handled. Every data tool then forwards the same bearer token to FastAPI, where
the active PostgreSQL account and current RBAC role are checked again.

This produces two enforcement points:

1. the MCP resource server rejects an invalid or expired token; and
2. the existing CSOS API rejects a disabled user or an unauthorized role.

## Approved MCP capabilities

The first gateway release is intentionally read-only.

| MCP primitive | Name or URI | CSOS source |
|---|---|---|
| Tool | `whoami` | PostgreSQL identity and RBAC |
| Tool | `search_assets` | Neo4j asset inventory |
| Tool | `get_asset` | Neo4j asset record |
| Tool | `list_security_findings` | Correlated Neo4j findings projection |
| Tool | `get_security_finding` | Finding investigation relationship chain |
| Tool | `get_topology` | Cyber Knowledge Graph topology projection |
| Tool | `list_attack_paths` | Ranked multi-hop graph analysis |
| Tool | `list_data_sources` | Configured collection source status |
| Tool | `get_ai_runtime_status` | Local AI runtime/model status |
| Tool | `get_executive_risk_summary` | Executive dashboard aggregation |
| Tool | `list_top_risks` | Risk projection |
| Tool | `get_compliance_coverage` | Compliance API |
| Resource | `csos://findings/summary` | Finding and security-gap KPIs |
| Resource | `csos://topology/current` | Current bounded topology |
| Resource | `csos://connectors/catalog` | Honest connector readiness catalog |
| Prompt | `investigate_finding` | Grounded finding investigation workflow |

Create/update/delete operations are not exposed. They remain in the existing
FastAPI application and retain their current Admin/Engineer restrictions.

## Run and check

Start the complete local stack:

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8001/health
```

The health response identifies `streamable-http` and `csos-jwt-bearer`. The MCP
endpoint itself returns `401 Unauthorized` until a valid CSOS access token is
provided.

Get a short-lived development access token:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@csos.com","password":"csos-demo"}'
```

Copy the returned `access_token` into the bearer-token field of an MCP client
and connect with the Streamable HTTP URL `http://localhost:8001/mcp`. In a
Codespace, use the forwarded HTTPS URL for port 8001 and set
`MCP_RESOURCE_URL`/`MCP_ISSUER_URL` to the public values when OAuth discovery is
required.

The current deployment is a bearer-token MCP resource server: CSOS login issues
the access token and the MCP client supplies it. It does not yet present CSOS as
a complete OAuth authorization server with an interactive authorization-code
flow. Existing sessions issued before the MCP audience/issuer update must sign
in again once to receive the new token claims.

## Deployment security

- Replace the documented development JWT secret in every non-development
  environment. Backend and MCP gateway values must match.
- TLS belongs at the reverse proxy or ingress boundary.
- Docker and Codespaces already supply a trusted reverse proxy, so the local
  template disables the SDK's second Host-header check. A direct production
  bind must enable `MCP_DNS_REBINDING_PROTECTION` and configure exact allowed
  hosts and origins.
- Access tokens are short-lived; refresh tokens are never accepted by MCP.
- The connector catalog distinguishes active platform sources from vendor
  adapters that still require credentials.

## Deployment boundary

The MCP gateway is connected to CSOS APIs, configured source status, and graph
data now. EDR/XDR, SIEM, CMDB, identity, cloud, firewall, and patch-management
adapter code is included. A customer source becomes live only when its
read-only endpoint and credential are configured and its mapping is validated;
these secrets are intentionally absent from source control. Collection writes
through the normalized ingestion boundary without changing MCP tool contracts.
