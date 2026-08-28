# Cyber Security Operating System (CSOS)

CSOS is an air-gapped-ready cybersecurity platform that combines a React web
application, FastAPI services, PostgreSQL, a Neo4j Cyber Knowledge Graph, and a
provider-independent AI layer with Ollama as the default local runtime.

**Status: Implementation Phase 3 (AI & Knowledge Graph Intelligence) is
complete and ready for stakeholder demonstration and customer deployment
configuration.** The repository includes persistent
authentication, RBAC administration, live dashboards, asset and vulnerability
management, Neo4j relationship management, bulk imports, audit history, and the
interactive Network Topology delivered in Phase 1. The current security
operations extension adds a correlated Security Findings workspace and a
layered, interface-aware topology generated from the Cyber Knowledge Graph.

Phase 3 adds an authenticated MCP Gateway, hardened collection layer,
configurable enterprise adapters, attack-path analytics, grounded specialist
agents, persistent AI chat, and local-model management. Customer credentials,
endpoints, approved network ranges, and any vendor-specific mappings are
deployment inputs; Phase 4 retains reporting, workflow, notification, and
standards-automation scope.

## Phase 1 deliverables

1. `docs/requirements/requirements.md` — functional and non-functional requirements
2. `docs/architecture/solution-architecture.md` — layered architecture, topology flow, and deployment
3. `docs/architecture/ai-agent-architecture.md` — provider-independent multi-agent design
4. `docs/wireframes/wireframes.md` — 12 core platform screens
5. `docs/roadmap/development-roadmap.md` — implementation-phase task list
6. `docs/implementation-readiness.md` — scope-to-evidence completion matrix
7. `database/postgresql/schema.sql` and `database/neo4j/schema.cypher` — platform data model
8. Runnable backend/frontend scaffold and Docker Compose environment

## Phase 2 deliverables

1. PostgreSQL-backed login with access/refresh token rotation and logout revocation
2. Seeded RBAC permissions and Administration Portal user/role management
3. Executive KPIs, asset/vulnerability distributions, compliance coverage, and top risks
4. Analyst investigation queue with risk, asset, and vulnerability context
5. Asset Inventory CRUD, classification, CSV/XLSX import, and relationship management
6. Vulnerability Repository CRUD, filtering, import, and asset linking
7. Audit logging for authentication and administrative/data changes
8. Neo4j Phase 2 demonstration data and OpenAPI-documented service endpoints
9. Correlated Security Findings dashboard with 19 security/asset fields,
   advanced filters, saved views, sorting, pagination, CSV export, and drill-down
10. Layered network/security topology with interface, IP, VLAN, vulnerability,
    risk, identity, and security-control context

## Phase 3 capability delivered

1. Standalone MCP 2.x resource server over Streamable HTTP
2. CSOS JWT bearer validation with issuer, audience, expiry, and token-type checks
3. Double-enforced RBAC through the gateway and existing FastAPI endpoints
4. Twelve read-only tools for identity, assets, findings, topology, attack paths,
   data sources, local AI status, risk, and compliance
5. Findings, topology, and connector-catalog resources plus an investigation prompt
6. SSH, SNMPv3, Nmap, Syslog, endpoint-agent, and enterprise REST collection
7. Encrypted connector credentials, scoped ingestion keys, scheduling, run history,
   target restrictions, and audit evidence
8. Normalized Neo4j correlation and ranked multi-hop attack paths
9. LangGraph specialist routing with persistent, cited, streamed chat responses
10. Ollama lifecycle and approved-model administration for air-gapped operation

## Repository layout

```text
csos-mvp/
├── docs/                         Planning, architecture, wireframes, roadmap
├── database/
│   ├── postgresql/schema.sql     Users, RBAC, audit, config, uploads, reports
│   └── neo4j/schema.cypher       Graph constraints, relationships, demo data
├── backend/
│   ├── .env.example              Safe local configuration template
│   └── app/
│       ├── ai/                    Provider-independent model adapters
│       ├── api/v1/                Versioned REST endpoints
│       ├── graph/                 Neo4j client and topology projection
│       ├── agents/                Grounded LangGraph specialist agents
│       ├── connectors/            Collection and enterprise adapters
│       ├── models/                SQLAlchemy/PostgreSQL models
│       └── schemas/               API request/response models
├── mcp-gateway/
│   └── csos_mcp/                  Authenticated MCP server and CSOS API client
├── frontend/
│   └── src/
│       ├── pages/                 Role-aware platform screens
│       ├── components/            Layout, chat, interactive topology graph
│       ├── contexts/              Authentication context
│       └── services/              API client
└── docker-compose.yml             Full local platform orchestration
```

## Run locally

Prerequisites: Docker Desktop with Compose support.

```bash
docker compose up --build
```

The Compose environment waits for PostgreSQL and Neo4j, initializes the Neo4j
schema and sample relationships automatically, starts the API, and then serves
the web application through Nginx.

- Web application: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- MCP endpoint: `http://localhost:8001/mcp`
- MCP health: `http://localhost:8001/health`
- Neo4j Browser: `http://localhost:7474`
- Development login: `admin@csos.com` / `csos-demo`

For local development without containers:

```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Platform delivery status

| Area | Current state |
|---|---|
| FastAPI routing, CORS, health endpoint, OpenAPI | Runnable |
| PostgreSQL authentication and JWT lifecycle | Implemented with bcrypt, refresh rotation, revocation, and session restoration |
| RBAC and Administration Portal | Implemented for user, role, permission, and audit operations |
| Executive and Analyst Dashboards | Implemented from Neo4j assets, risks, vulnerabilities, and controls |
| Asset Inventory and relationships | Implemented with CRUD, classification, import, and Neo4j relationship management |
| Vulnerability Repository | Implemented with CRUD, filtering, import, and asset linking |
| Correlated Security Findings | Implemented with security-gap KPIs, advanced filtering, saved views, CSV export, and finding/asset drill-down |
| PostgreSQL schema and matching SQLAlchemy models | Implemented and initialized automatically at application startup |
| Neo4j schema, relationships, automatic local seed | Runnable through Docker Compose |
| Network Topology API and interactive graph screen | Implemented from bounded Neo4j projections with semantic layers, interface labels, risk colors, filtering, and relationship highlighting |
| Asset relationship topology tab | Implemented; focuses the selected asset's neighborhood |
| Provider-independent model boundary | Implemented; Ollama default with configurable compatible models |
| MCP Gateway | Implemented as an authenticated, read-only Streamable HTTP resource server over approved CSOS APIs |
| Collection and enterprise connectors | SSH, SNMPv3, Nmap, Syslog, endpoint agent, and configurable EDR/XDR, SIEM, CMDB, identity, cloud, firewall, and patch REST adapters implemented; customer credentials/mappings are deployment inputs |
| LangGraph orchestrator | Implemented with specialist routing, grounded context, persistent history, citations, traces, streaming, and local fallback |
| Local AI models | Ollama health, approved-model install and validation UI implemented |
| Risk and compliance intelligence | Grounded specialist retrieval and multi-hop attack paths implemented; Phase 4 retains workflow/report delivery scope |

## AI model configuration

Ollama is the default local runtime. Models are selected from environment
configuration rather than being hard-coded into agents:

```dotenv
AI_PROVIDER=ollama
AI_DEFAULT_MODEL=llama3.1
AI_AVAILABLE_MODELS=llama3.1,deepseek-r1,qwen2.5,mistral,allam
```

Additional Llama, DeepSeek, Qwen, Mistral, ALLAM, HUMAIN-compatible, or other
sovereign/open models can be enabled when available in an Ollama-compatible
package. New runtime providers implement the same model-provider interface, so
agent and application architecture does not need to change.

## Validation

```bash
cd backend && pytest
cd mcp-gateway && pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

See `docs/phase-3-completion.md` for deployment and acceptance,
`docs/security-findings-and-topology.md` for security operations behavior,
`docs/mcp-gateway.md` for MCP usage, and
`docs/roadmap/development-roadmap.md` for Phase 4 scope.
