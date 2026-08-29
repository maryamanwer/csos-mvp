# Phase 3 Completion and Deployment Guide

Implementation provenance and the boundary between reference material and the
CSOS-owned design are documented in `implementation-provenance.md`.

## Delivered application capability

Phase 3 application development is complete in this repository:

- authenticated, read-only MCP Gateway with CSOS JWT and RBAC enforcement;
- normalized collection for SSH, SNMPv3, Nmap XML, Syslog, and the CSOS endpoint agent;
- configurable read-only REST adapters for EDR/XDR, SIEM, CMDB, identity,
  cloud, firewall, and patch-management platforms;
- encrypted connector credentials, rotatable encryption keys, scoped ingestion
  API keys, target-network restrictions, audit records, run scheduling, and
  collection history;
- correlation of collected assets, interfaces, vulnerabilities, and data-source
  evidence into Neo4j;
- multi-hop attack-path analysis and topology security overlay;
- LangGraph routing across Asset Intelligence, Risk Assessment, and Compliance
  agents;
- local Ollama health, approved-model installation/validation, persistent chat
  conversations, grounded citations, traces, streaming, and deterministic
  knowledge-graph fallback;
- Data Sources and Local AI Models administration screens.

## Deployment boundary

The software adapters are runnable now. A customer environment becomes live
only after its administrator supplies the vendor endpoint, read-only service
credential, approved target ranges, and (where a vendor response differs from
the common field names) a verified field mapping. This is deployment
configuration, not a missing dashboard or platform component. CSOS never
claims a vendor is connected until a saved source has completed a successful
collection run.

## Air-gapped deployment checklist

1. Mirror the repository, container images, Python/Node packages, and approved
   Ollama model files into the controlled network using the organization's
   media-transfer process.
2. Replace all development secrets. Set a strong `JWT_SECRET_KEY` and a
   separate `CONNECTOR_ENCRYPTION_KEYS` key ring; configure the same JWT values
   for the API and MCP Gateway.
3. Restrict `CONNECTOR_ALLOWED_CIDRS` to approved management networks and allow
   only required outbound destinations from the collection workers.
4. Start the Compose stack, verify PostgreSQL and Neo4j health, then validate
   the API and MCP `/health` endpoints.
5. Install an approved local Ollama model from the internal registry or model
   archive and validate it on **Local AI Models**.
6. Add each live source on **Data Sources & Collection**, test it, run it, and
   confirm the run history and correlated graph records.
   SSH collection verifies trusted host keys by default and SNMPv3 requires
   authenticated, encrypted `authPriv` credentials.
7. Create scoped endpoint-agent or Syslog keys only when needed. Copy each key
   once, distribute it through the organization's secret-management channel,
   and revoke it after decommissioning.
8. Validate Security Findings, attack paths, AI citations, and MCP tool access
   with representative customer data before production acceptance.

## Common enterprise REST contract

The generic enterprise adapters accept common JSON envelopes such as `items`,
`data`, `results`, `assets`, or `findings`. Asset records can use common aliases
including `id`, `asset_id`, `hostname`, `ip`, `operating_system`, `owner`,
`criticality`, `edr_status`, and `data_sources`. Finding records can use `id`,
`cve`, `severity`, `cvss`, `status`, `asset_id`/`asset_ids`, `first_detected`,
`last_seen`, `due_at`, and `remediation`.

If a vendor uses a materially different API or pagination scheme, implement a
small connector subclass that emits the same canonical collection objects.
The graph, findings dashboard, AI agents, and MCP tools do not need to change.

## Acceptance checks

```bash
docker compose config
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8001/health

cd backend && pytest
cd ../mcp-gateway && pytest
cd ../frontend && npm run build
```

Expected portal demonstration:

1. **Data Sources** — configure/test/run a source and show its run history.
2. **Network Topology** — show network zones, correlated evidence, and ranked
   attack paths.
3. **Security Findings** — show the unified finding/asset/source/SLA view.
4. **Local AI Models** — show runtime health and the installed approved model.
5. **AI Chat Assistant** — ask a risk question and show citations plus the
   specialist-agent trace.
6. **MCP** — call `whoami`, list the approved tools, and retrieve a read-only
   finding or topology result with an authenticated CSOS token.
