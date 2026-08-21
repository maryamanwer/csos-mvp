# Phase 3 MCP Gateway Release Notes

## Summary

This increment connects CSOS to the Model Context Protocol through a dedicated,
authenticated Streamable HTTP gateway. MCP hosts and future CSOS agents can now
discover and call approved platform capabilities using the same user identity
and RBAC boundary as the web application.

## Delivered

- Official MCP Python SDK 2.0 service on port 8001.
- CSOS access-JWT bearer authentication with issuer and MCP audience checks.
- Secondary active-user and role verification through the existing FastAPI APIs.
- Nine read-only tools covering identity, assets, findings, topology, executive
  risk, top risks, and compliance coverage.
- Three context resources for findings KPIs, topology, and connector readiness.
- Grounded finding-investigation prompt template.
- Docker Compose orchestration and health check.
- Backend token/audience regression tests and MCP protocol/auth/tool-call tests.

## Explicitly remaining

- Vendor credentials and live adapters for EDR/XDR, SIEM, CMDB, identity,
  cloud, firewall, and patch-management systems.
- Full OAuth authorization-code flow for third-party interactive MCP clients.
- AI-agent runtime registration and autonomous MCP tool selection.
- Production TLS/ingress configuration and environment-specific Host/Origin
  allowlists.
