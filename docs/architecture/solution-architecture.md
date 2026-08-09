# CSOS – Solution Architecture

## 1. Layered Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│ 1. Presentation Layer (React + TypeScript + MUI)                 │
│    Dashboards, Findings, Network Topology, AI Chat, Reports      │
├──────────────────────────────────────────────────────────────────┤
│ 2. Application Layer (FastAPI, Python)                           │
│    Auth/RBAC, Assets, Topology Projection, Risk, Compliance      │
├──────────────────────────────────────────────────────────────────┤
│ 2.5 Custom Standards & Policies Input Layer                      │
│    Upload (CSV/Excel/Word/JSON/Manual) → Normalize → Map         │
├──────────────────────────────────────────────────────────────────┤
│ 3. AI Layer (LangGraph + LangChain + Model Provider Boundary)    │
│    Orchestrator → Asset / Risk / Compliance / Chat               │
│    Default local runtime: Ollama                                  │
├──────────────────────────────────────────────────────────────────┤
│ 4. Cyber Knowledge Graph (Neo4j) — Relationship Source of Truth │
├──────────────────────────────────────────────────────────────────┤
│ 5. Platform Data (PostgreSQL)                                    │
│    Users, RBAC, audit, settings, uploads, report metadata        │
├──────────────────────────────────────────────────────────────────┤
│ 6. Infrastructure (Docker Compose)                               │
└──────────────────────────────────────────────────────────────────┘
```

## 2. Component Responsibilities

| Layer | Component | Responsibility | Technology |
|---|---|---|---|
| Presentation | Web App | Role-aware UI for security and compliance teams | React 18, TypeScript, MUI |
| Presentation | Topology Workspace | Pan, zoom, filter, search, select, and explore graph relationships | React SVG |
| Application | API Gateway | Routing, authorization dependencies, validation, OpenAPI | FastAPI |
| Application | Auth Service | Login, JWT lifecycle, RBAC | FastAPI, python-jose, passlib |
| Application | Asset Service | Inventory, classification, relationships | FastAPI, Neo4j |
| Application | Findings Projection | Correlate asset, vulnerability, risk, control, identity, and adapter context without duplicating source entities | FastAPI, Neo4j driver |
| Application | Topology Projection | Convert stored Neo4j entities/relationships and interfaces into bounded UI graph data | FastAPI, Neo4j driver |
| Application | Risk Engine | Score and prioritize risk | FastAPI |
| Application | Compliance Engine | Framework/control mapping | FastAPI |
| Input | Standards Ingestor | Parse, normalize, and map uploaded controls | pandas, python-docx, openpyxl |
| AI | Orchestrator | Route requests to grounded specialist agents | LangGraph |
| AI | Model Provider Boundary | Resolve configured provider/model without coupling agents to a vendor | Python provider adapters |
| AI | Ollama Adapter | Run compatible models locally or in an air-gapped network | Ollama |
| Data | PostgreSQL | Users, auth, configuration, audit logs | PostgreSQL 16 |
| Data | Neo4j | Assets, identities, risks, vulnerabilities, controls, policies, frameworks, relationships | Neo4j 5 |
| Infrastructure | Docker Compose | Local orchestration, health checks, graph initialization | Docker |

## 3. Network Topology Data Flow

1. Assets and relationships are created manually, imported, or written by future connectors.
2. Neo4j remains the source of truth for graph entities and relationship types.
3. `GET /api/v1/topology` requests a bounded graph projection; an optional asset ID narrows it to the asset's direct neighborhood.
4. The API returns explicit nodes and edges with stable entity IDs, types, labels, risk context, edge categories, and interface metadata when stored.
5. The React topology workspace renders semantic network/security layers and applies search, filters, pan, zoom, fit-to-screen, node/edge selection, relationship highlighting, and detail inspection.
6. No live network discovery is required for this flow. Future discovery connectors write into the same graph and the visualization updates without an architecture change.

## 4. Security Findings Correlation Flow

1. Source adapters or imports normalize asset, vulnerability, risk, identity,
   control, ownership, EDR, and observation metadata into the Cyber Knowledge
   Graph.
2. `GET /api/v1/findings` performs one bounded Neo4j projection across those
   stored relationships and applies authorized search, filtering, sorting, and
   pagination on the server.
3. The Security Findings workspace presents one correlated row per
   asset/finding pair rather than isolated copies from every tool.
4. Finding drill-down exposes the investigation chain from asset and owner to
   vulnerability, controls, risks, identities, and recommended remediation.
5. `GET /api/v1/findings/export` applies the same filters to a bounded CSV
   export. Saved views remain user-browser preferences and do not alter source
   data.
6. Future connector or MCP services write through the same normalization
   boundary; the dashboard and graph contracts do not depend on a particular
   security vendor.

## 5. AI Investigation Data Flow

1. A user asks the AI Chat Assistant a security or compliance question.
2. The Orchestrator classifies intent and routes to the appropriate specialist agent.
3. The specialist retrieves authorized facts from Neo4j/PostgreSQL before generation.
4. The configured model provider resolves the selected compatible model and generates a grounded explanation.
5. The Chat Assistant returns a role-appropriate response with source entity/control IDs and an agent trace.

## 6. Deployment Topology

```text
docker-compose.yml
 ├── frontend        Nginx + React; proxies /api to backend   :3000
 ├── backend         FastAPI + Uvicorn                        :8000
 ├── postgres        PostgreSQL 16                            :5432
 ├── neo4j           Neo4j 5 Community                        :7474 / :7687
 ├── neo4j-init      One-shot schema and demo relationship load
 └── ollama          Local model runtime                       :11434
```

All mandatory platform services can run in-network. Ollama supports local model
inference without an external API call. The Compose stack waits for database
health, initializes the graph idempotently, and starts the web tier only after
the API becomes healthy.

## 7. Security Model

- JWT bearer access and refresh tokens.
- RBAC enforced by FastAPI dependencies.
- Password hashes stored with bcrypt when PostgreSQL authentication is enabled.
- Audit records for authentication and sensitive administrative actions.
- Bounded topology query limits and validated request parameters.
- Bounded findings pagination/export and allow-listed sort fields.
- Development credentials are isolated to the documented development environment.

## 8. Extension Points

- New AI models are added through configuration; new runtimes implement the model-provider interface.
- New agents plug into the LangGraph orchestrator without changing existing agents.
- Enterprise connectors implement a common connector interface and write normalized graph entities/relationships.
- Future MCP servers expose approved connector tools through a gateway; MCP is an integration boundary, not a replacement for authorization, normalization, or the Cyber Knowledge Graph.
- Live topology synchronization consumes the same Neo4j model and API contract.
- Attack-path analysis consumes the same graph without replacing the topology visualization.
