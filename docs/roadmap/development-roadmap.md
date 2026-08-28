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

- [x] PostgreSQL-backed authentication, access/refresh JWT lifecycle, bcrypt hashing
- [x] RBAC middleware completion and role seed management
- [x] Administration Portal user/role/audit operations
- [x] Executive Dashboard KPI and trend widgets
- [x] Analyst Dashboard investigation queue
- [x] Asset Inventory CRUD, classification, and CSV/Excel import
- [x] Asset relationship management in Neo4j
- [x] Vulnerability Repository CRUD and import
- [x] Correlated Security Findings dashboard, advanced filters, export, saved views, and drill-down
- [x] Security-gap KPIs for EDR, critical exposure, controls, unmanaged assets, and SLA breaches
- [x] Interface-aware layered topology with network, vulnerability, risk, identity, and control relationships
- [x] OpenAPI-documented service completion for the above

## Implementation Phase 3 – AI & Knowledge Graph Intelligence

- [x] Add authenticated MCP Gateway with approved CSOS tools and resources
- [x] Reuse CSOS JWT identity and enforce existing FastAPI RBAC on MCP tool calls
- [x] Extend normalized domain persistence for live enterprise connector payloads
- [x] Advanced multi-hop attack-path queries and ranked path comparison
- [x] Complete LangGraph Orchestrator routing
- [x] Complete Asset Intelligence, Risk Assessment, and Compliance Agents
- [x] Stream AI Chat responses with grounded citations and agent traces
- [x] Ollama lifecycle, health checks, and model-management UI
- [x] Validate configured Llama, DeepSeek, Qwen, Mistral, ALLAM, and compatible sovereign models
- [x] Add configurable EDR/XDR, SIEM, CMDB, identity, cloud, firewall, and patch adapters
- [x] Add SSH, SNMPv3, Nmap, Syslog, and endpoint-agent collection
- [x] Encrypt connector credentials and add scoped ingestion keys, scheduling, audit, and run history

Customer vendor credentials, endpoints, network approvals, and optional
vendor-specific field mappings are deployment inputs described in
`docs/phase-3-completion.md`; they are not stored in source control.

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
