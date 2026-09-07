# Current handover

This source includes additional implementation beyond the original Phase 2 release. Read [the implementation review](docs/completion-review.md) for delivered features and remaining work, and [operations](docs/operations.md) for startup and validation. The original release description below is historical and does not establish completion of later phases.

# Cyber Security Operating System (CSOS)

CSOS is an air-gapped-ready cybersecurity platform that combines a React web
application, FastAPI services, PostgreSQL, a Neo4j Cyber Knowledge Graph, and a
provider-independent AI layer with Ollama as the default local runtime.

**Status: Implementation Phase 2 (Core Platform Development) is complete and
ready for stakeholder demonstration.** The repository now includes persistent
authentication, RBAC administration, live dashboards, asset and vulnerability
management, Neo4j relationship management, bulk imports, audit history, and the
interactive Network Topology delivered in Phase 1.

AI intelligence, advanced graph analytics, reporting, and remaining workflow
automation are explicitly scheduled in Phases 3 and 4.

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
│       ├── agents/                LangGraph agent scaffold
│       ├── models/                SQLAlchemy/PostgreSQL models
│       └── schemas/               API request/response models
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
| PostgreSQL schema and matching SQLAlchemy models | Implemented and initialized automatically at application startup |
| Neo4j schema, relationships, automatic local seed | Runnable through Docker Compose |
| Network Topology API and interactive graph screen | Implemented; generated from Neo4j relationships |
| Asset relationship topology tab | Implemented; focuses the selected asset's neighborhood |
| Provider-independent model boundary | Implemented; Ollama default with configurable compatible models |
| LangGraph orchestrator | Compiles; model-driven reasoning and streaming are Phase 3 |
| Risk, compliance, reporting, standards ingestion | Foundations exist; advanced intelligence and delivery follow Phases 3 and 4 |

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
cd frontend && npm run build
```

See `docs/roadmap/development-roadmap.md` for the next implementation phase.
