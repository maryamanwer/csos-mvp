# Cyber Security Operating System (CSOS)

CSOS is an air-gapped-ready cybersecurity platform that combines a React web
application, FastAPI services, PostgreSQL, a Neo4j Cyber Knowledge Graph, and a
provider-independent AI layer with Ollama as the default local runtime.

**Status: the Initial Release defined in the Business Analysis Document is
implemented and ready for stakeholder acceptance testing.** Live enterprise
connectors, automated discovery, attack-path generation, high availability and
mobile clients remain future-phase capabilities as defined in the approved scope.

The release includes persistent authentication, database-backed RBAC,
role-aware dashboards, asset/identity and vulnerability management, Neo4j
topology, explainable risk scoring, compliance gap analysis, custom standards,
LangGraph/Ollama assistance, PDF/Excel reporting, remediation workflows and
audit history. See [client acceptance](docs/client-acceptance.md) and
[operations](docs/operations.md).

## Run in GitHub Codespaces

Create a Codespace for this branch. The included development-container setup
provides Docker inside the Codespace and forwards the application ports. Then run:

```bash
docker compose up --build -d
docker compose exec ollama ollama pull llama3.1
docker compose ps
```

Open the forwarded **CSOS Web** port 3000 and keep port visibility private.
Use a Codespace with at least 4 cores and 16 GB RAM when demonstrating local AI.

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
| LangGraph orchestrator | Role-grounded Asset, Risk and Compliance agents with evidence and history |
| Risk, compliance, reporting, standards ingestion | Implemented for the agreed Initial Release scope |

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
