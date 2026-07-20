# CSOS – Development Roadmap

## Milestone 1 – Planning & Architecture (1 week) — $300
- [x] Requirements gathering (`docs/requirements/requirements.md`)
- [x] Solution architecture (`docs/architecture/solution-architecture.md`)
- [x] AI agent architecture (`docs/architecture/ai-agent-architecture.md`)
- [x] UI wireframes (`docs/wireframes/wireframes.md`)
- [x] PostgreSQL schema (`database/postgresql/schema.sql`)
- [x] Neo4j schema (`database/neo4j/schema.cypher`)
- [x] Repo scaffold (this repository)

## Milestone 2 – Core Platform Development (2–3 weeks) — $700
- [ ] Auth service: login, JWT issue/refresh, bcrypt hashing
- [ ] RBAC middleware + role seed data
- [ ] Administration Portal (users, roles, audit log)
- [ ] Executive Dashboard (KPIs, risk trend widgets)
- [ ] Analyst Dashboard (investigation queue)
- [ ] Asset Inventory CRUD + classification + CSV import
- [ ] Asset relationships persisted to Neo4j
- [ ] Vulnerability Repository CRUD + CSV import
- [ ] REST APIs for all of the above, documented in OpenAPI/Swagger

## Milestone 3 – AI & Knowledge Graph (2–3 weeks) — $600
- [ ] Neo4j Knowledge Graph wired to Asset/Vuln/Risk/Policy models
- [ ] Graph query endpoints (relationships, path queries)
- [ ] LangGraph Orchestrator Agent
- [ ] Asset Intelligence, Risk Assessment, Compliance Agents
- [ ] AI Chat Assistant UI + streaming responses
- [ ] Ollama integration (model pull, health check)
- [ ] Docker Compose environment (all services)

## Milestone 4 – MVP Completion & Delivery (2 weeks) — $400
- [ ] MVP Risk Engine scoring finalized
- [ ] MVP Compliance Engine (framework mapping, gap dashboard)
- [ ] Reporting (PDF/Excel export)
- [ ] Workflow Engine (MVP state machine)
- [ ] Notification Service (email/webhook stub)
- [ ] Custom Standards & Policy upload (CSV, Excel, Word, JSON, manual)
- [ ] Control-to-asset mapping UI
- [ ] Testing (unit + integration smoke tests)
- [ ] Documentation + Deployment Guide
- [ ] Docker production-style deployment
- [ ] Source code handover

## Definition of Done (per milestone)
1. Feature runs locally via `docker-compose up`.
2. Endpoints documented in Swagger (`/docs`).
3. Basic tests pass (`pytest` backend, `npm test` frontend where applicable).
4. Demo walkthrough recorded/screenshared with stakeholder.
