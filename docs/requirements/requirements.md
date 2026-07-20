# CSOS – Requirements Specification (Milestone 1)

## 1. Purpose
Define the functional and non-functional requirements for the Cyber Security Platform (CSOS) MVP, as scoped in the CSOS MVP Scope Clarification document.

## 2. User Roles
| Role | Description | Primary Screens |
|---|---|---|
| CISO / Executive | Strategic oversight, KPIs, risk trends | Executive Dashboard, Reports |
| Security Architect | Designs controls, reviews architecture | Asset Inventory, Knowledge Graph |
| Security Analyst | Investigates, triages, responds | Analyst Dashboard, AI Chat |
| Security Engineer | Implements controls, manages assets | Asset Inventory, Asset Details |
| Compliance Officer | Manages frameworks & audits | Compliance Dashboard, Custom Standards |
| Administrator | User, role, and system management | Administration Portal |

## 3. Functional Requirements (MVP scope)

### FR-1 Authentication & RBAC
- FR-1.1 Users authenticate via username/password, issued a JWT.
- FR-1.2 Roles: Admin, Executive, Analyst, Engineer, Compliance Officer.
- FR-1.3 Every API endpoint enforces role-based authorization.

### FR-2 Asset Management
- FR-2.1 CRUD for assets (servers, apps, network devices, identities).
- FR-2.2 Asset classification (criticality, data sensitivity, environment).
- FR-2.3 Asset relationships stored and queryable via the Knowledge Graph.
- FR-2.4 CSV/Excel bulk import of assets.

### FR-3 Vulnerability Repository
- FR-3.1 Store vulnerabilities linked to assets (CVE id, severity, status).
- FR-3.2 Manual entry + CSV import (scanner integrations are mocked in MVP).

### FR-4 Risk Engine (MVP implementation)
- FR-4.1 Compute a risk score per asset from severity, exposure, criticality.
- FR-4.2 Risk Dashboard with prioritized risk list.

### FR-5 Compliance Engine (MVP implementation)
- FR-5.1 Map controls to frameworks (built-in: ISO 27001, NIST CSF) and custom standards.
- FR-5.2 Compliance Dashboard showing coverage/gaps per framework.

### FR-6 Custom Standards & Policies
- FR-6.1 Upload standards/policies as PDF, Excel, Word, CSV, JSON.
- FR-6.2 Manual entry of controls and checklist items.
- FR-6.3 Map uploaded controls to assets/frameworks.

### FR-7 AI Layer (Multi-Agent)
- FR-7.1 Orchestrated agents: Asset Intelligence, Risk Assessment, Compliance, Chat Assistant.
- FR-7.2 LangGraph state graph coordinates agent hand-off.
- FR-7.3 Local LLM via Ollama (Llama 3.x / Mistral / Qwen), OpenAI-compatible optional.

### FR-8 Cyber Knowledge Graph
- FR-8.1 Neo4j stores assets, identities, vulnerabilities, risks, controls, policies and their relationships.
- FR-8.2 Graph queries exposed via REST API for the UI and AI agents.

### FR-9 Reporting
- FR-9.1 Generate PDF/Excel exports for risk, compliance, and asset reports.

### FR-10 Administration
- FR-10.1 User management, role assignment, audit log viewer.

## 4. Non-Functional Requirements
- NFR-1 Deployable via Docker Compose (dev) with air-gapped operation support (no external calls required at runtime).
- NFR-2 REST APIs documented via OpenAPI/Swagger.
- NFR-3 Passwords hashed (bcrypt), JWT with expiry & refresh.
- NFR-4 All layers containerized independently (frontend, backend, postgres, neo4j, ollama).
- NFR-5 Codebase organized for extension (new agents, new connectors) without core rewrites.

## 5. Out of Scope (MVP)
See "Out of Scope" section in the CSOS MVP Scope Clarification document — live third-party integrations (AD, SIEM, EDR, scanners, cloud), HA/clustering, mobile app, automated discovery, attack-path automation.

## 6. Acceptance Criteria (Milestone 1)
- [ ] This requirements document reviewed & approved
- [ ] Solution architecture document reviewed & approved
- [ ] PostgreSQL schema drafted and reviewed
- [ ] Neo4j schema drafted and reviewed
- [ ] AI agent architecture drafted and reviewed
- [ ] Development roadmap agreed
- [ ] Repo scaffold created (this deliverable)
