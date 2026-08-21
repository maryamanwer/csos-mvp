# CSOS Security Findings and Topology

This document describes the delivered security-operations extension. The user
experience takes conceptual inspiration from modern cyber asset and exposure
management products while using CSOS branding, its existing MUI design system,
and its Cyber Knowledge Graph architecture.

## Security Findings workspace

`/findings` provides a correlated view of vulnerabilities and their affected
assets. Each row contains finding/CVE identity, hostname, type, criticality,
owner, IP, operating system, EDR coverage and product, severity/CVSS, CSOS risk
score and level, workflow status, detection dates, SLA, connected data sources,
and recommended remediation.

The workspace supports:

- free-text search and advanced filtering by risk, criticality, severity, EDR,
  asset type, owner, status, and data source;
- allow-listed server-side sorting and pagination;
- browser-persisted saved views;
- a bounded CSV export that applies the active filters;
- finding drill-down across asset, owner, vulnerability, controls, risk, and
  remediation; and
- direct navigation to the affected asset record.

Summary cards identify six operational gap classes: critical assets without
EDR, critical findings on critical assets, outdated EDR agents, missing
controls, unknown/unmanaged assets, and findings outside SLA.

## Correlation model

The table does not create a second vulnerability store. The API projects a
correlated view from Neo4j relationships among `Asset`, `Vulnerability`,
`Risk`, `Control`, and `Identity` entities. Source-adapter names are preserved
on normalized asset and vulnerability observations and returned as one union.

The current repository supports imports and seeded demonstration observations.
EDR/XDR, vulnerability management, CMDB, identity, SIEM, cloud, network,
firewall, and patch-management products can later write to the same normalized
model through connector services. The delivered MCP gateway now exposes
approved, read-only CSOS tools and resources without bypassing RBAC or making
the UI vendor-specific. Live vendor adapters still require credentials and
source-specific mappings.

## Network and security topology

`/topology` requests a bounded graph from Neo4j and arranges stored nodes in a
Visio-style network map rather than a circular layout. The default view focuses
on the operational network path with recognizable device glyphs, subnet zones,
interface names on the relevant connectors, orthogonal routing, and readable
asset labels. Segment membership
is derived from `HAS_INTERFACE` and `LOCATED_IN` relationships, while connected
assets without direct interface metadata inherit the nearest stored zone. The
demonstration path is:

```text
Internet → Firewall → Core Switch → Web Server → Application Server → Database
```

The optional security overlay adds stored vulnerabilities, risks, identities,
controls, policies, and frameworks without crowding the default network map.
Orthogonal network connectors and routed overlay connections reduce visual
collisions, while edge labels are limited to primary network paths or the
selected relationship. Interface and protocol/port details are shown only when
they exist in Neo4j.

The topology provides pan, zoom, fit-to-screen, search, entity/risk/environment/
relationship filters, node and edge selection, tooltips, relationship legends,
and a details panel. Selecting an entity highlights its direct neighborhood and
dims unrelated nodes and edges. Asset risk uses the highest related risk/CVSS
for its primary visual state. If an imported asset has not yet been correlated
to a finding, its criticality is used as a conservative visual fallback rather
than incorrectly showing it as low risk:

- High: red
- Medium: orange
- Low: green

The underlying detailed risks remain unchanged and visible in the panel.

## APIs

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/findings` | Filtered, sorted, paginated correlated findings |
| `GET` | `/api/v1/findings/summary` | Security-finding and gap KPIs |
| `GET` | `/api/v1/findings/export` | Bounded CSV export using active filters |
| `GET` | `/api/v1/findings/{finding_id}` | Finding relationship context for one asset |
| `GET` | `/api/v1/topology` | Bounded full or entity-focused Neo4j graph |

All endpoints use existing JWT/RBAC dependencies. Findings sorting is
allow-listed, export is capped, and topology node/relationship limits are
validated.

## Demonstration data

`database/neo4j/schema.cypher` idempotently creates clearly identified sample
assets and relationships needed for an immediate product walkthrough. They are
not random or production data. Reinitialize an existing development volume with:

```bash
docker compose run --rm neo4j-init
```

Then refresh the Findings or Network Topology workspace. For a completely clean
development database, remove only the named CSOS development volumes and start
Compose again; do not use that operation against production data.

## Current integration boundary

- Implemented now: imports, normalized Neo4j data, correlation API, findings
  workspace, topology projection, investigation UI, and an authenticated MCP
  gateway over existing CSOS APIs.
- Designed for later: credentialed live connector ingestion, agent-driven MCP
  tool calls, automated discovery, and multi-hop attack-path analytics.

This separation keeps the current platform truthful and runnable while allowing
new security sources to be added without rewriting the dashboard or topology.
