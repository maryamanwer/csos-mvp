# CSOS – Development Roadmap

## Implementation Phase 1 – Planning & Architecture

- [x] Requirements specification (`docs/requirements/requirements.md`)
- [x] Solution architecture (`docs/architecture/solution-architecture.md`)
- [x] Provider-independent AI agent architecture (`docs/architecture/ai-agent-architecture.md`)
- [x] UI wireframes including interactive Network Topology (`docs/wireframes/wireframes.md`)
- [x] PostgreSQL schema (`database/postgresql/schema.sql`)
- [x] Neo4j Cyber Knowledge Graph schema and seed relationships (`database/neo4j/schema.cypher`)
- [x] Runnable repository scaffold with configuration template
- [x] Neo4j-backed topology projection API and interactive UI foundation
- [x] Docker Compose health checks, graph initialization, and frontend API proxy
- [x] Focused automated tests and build validation

## Implementation Phase 2 – Core Platform Development

- [ ] PostgreSQL-backed authentication, access/refresh JWT lifecycle, bcrypt hashing
- [ ] RBAC middleware completion and role seed management
- [ ] Administration Portal user/role/audit operations
- [ ] Executive Dashboard KPI and trend widgets
- [ ] Analyst Dashboard investigation queue
- [ ] Asset Inventory CRUD, classification, and CSV/Excel import
- [ ] Asset relationship management in Neo4j
- [ ] Vulnerability Repository CRUD and import
- [ ] OpenAPI-documented service completion for the above

## Implementation Phase 3 – AI & Knowledge Graph Intelligence

- [ ] Complete domain model persistence in Neo4j
- [ ] Advanced graph queries and path exploration
- [ ] Complete LangGraph Orchestrator routing
- [ ] Complete Asset Intelligence, Risk Assessment, and Compliance Agents
- [ ] Stream AI Chat responses with grounded citations and agent traces
- [ ] Ollama lifecycle, health checks, and model-management UI
- [ ] Validate configured Llama, DeepSeek, Qwen, Mistral, ALLAM, and compatible sovereign models
- [ ] Add live connectors through the common connector interface

## Implementation Phase 4 – Platform Completion & Delivery

- [ ] Finalize explainable risk scoring
- [ ] Finalize compliance mapping and gap analysis
- [ ] PDF/Excel reporting and report history
- [ ] Workflow state engine
- [ ] Notification service
- [ ] Custom standards/policy parsing and control mapping
- [ ] Expanded unit, integration, security, and end-to-end test suites
- [ ] Production deployment guide and operational runbooks
- [ ] Source-code handover

## Definition of Done

1. The phase runs locally through `docker compose up --build`.
2. New endpoints appear in Swagger at `/docs`.
3. Relevant backend tests and the frontend production build pass.
4. Security-sensitive defaults are documented and are not presented as production settings.
5. The stakeholder receives a demonstrable walkthrough and release notes.
