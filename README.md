# CSOS — Cyber Security Platform (MVP)

Repo scaffold for the Cyber Security Platform MVP: React + FastAPI + PostgreSQL +
Neo4j + LangGraph/LangChain + Ollama, Docker-deployed, air-gapped-ready.

**Status:  (Planning & Architecture) delivered as this scaffold.**
Everything under `backend/app` and `frontend/src` is a real, importable/runnable
structure with working stubs — routes respond, pages render, the LangGraph
orchestrator compiles — but nothing is wired to a live database or LLM yet.
Every stub is marked `TODO(M2)/(M3)/(M4)` showing exactly which milestone
implements it for real. See `docs/roadmap/development-roadmap.md` for the
full build order.

## Read first
1. `docs/requirements/requirements.md` — functional & non-functional requirements
2. `docs/architecture/solution-architecture.md` — layered architecture, data flow, deployment
3. `docs/architecture/ai-agent-architecture.md` — multi-agent design (LangGraph)
4. `docs/wireframes/wireframes.md` — the 11 MVP screens
5. `docs/roadmap/development-roadmap.md` — milestone-by-milestone task list
6. `database/postgresql/schema.sql` + `database/neo4j/schema.cypher` — data model

## Repo layout
```
csos-mvp/
├── docs/                        Milestone 1 deliverables
├── database/
│   ├── postgresql/schema.sql     Users, RBAC, audit, config, uploads, reports
│   └── neo4j/schema.cypher       Cyber Knowledge Graph: constraints + relationships
├── backend/
│   └── app/
│       ├── main.py                FastAPI entrypoint
│       ├── core/                  config.py, security.py (JWT/RBAC), database.py
│       ├── api/v1/                auth, assets, risk, compliance, standards, chat, reports, admin
│       ├── models/                SQLAlchemy models (Postgres)
│       ├── schemas/                Pydantic request/response schemas
│       ├── graph/                  Neo4j client wrapper
│       └── agents/                 LangGraph orchestrator + Asset/Risk/Compliance/Chat agents
├── frontend/
│   └── src/
│       ├── pages/                  11 MVP screens
│       ├── components/             AppLayout (role-aware nav), ChatPanel
│       ├── contexts/                AuthContext
│       ├── services/                api.ts (axios client)
│       └── theme.ts                 CSOS design system
└── docker-compose.yml            postgres + neo4j + ollama + backend + frontend
```

## Running locally (once M2+ dependencies are installed)
```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Or everything via Docker
docker-compose up --build
```

## What's real vs mocked in this scaffold
| Area | State |
|---|---|
| FastAPI app, routing, CORS, health check | Real, runs today |
| JWT issue/verify, RBAC dependency | Real logic; login uses a mock user until M2 wires the DB |
| SQLAlchemy models matching `schema.sql` | Real, ready for Alembic autogenerate |
| Neo4j client + example Cypher queries | Real; needs a running Neo4j instance |
| LangGraph orchestrator graph (compiles, runs end-to-end) | Real graph wiring; agent "reasoning" is stubbed (no LLM call yet — that's M3) |
| React pages, routing, role-aware nav, theme | Real, renders today |
| API calls from frontend to backend | Real, will show data once backend is DB-connected |

## Next milestone
See `docs/roadmap/development-roadmap.md` → **Milestone 2 – Core Platform Development.**
