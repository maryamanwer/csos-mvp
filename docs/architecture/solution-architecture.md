# CSOS – Solution Architecture (Milestone 1)

## 1. Layered Architecture

```
┌───────────────────────────────────────────────────────────┐
│ 1. Presentation Layer  (React + TypeScript + MUI)          │
│    Executive/Analyst Dashboards, AI Chat, Reports, Admin   │
├───────────────────────────────────────────────────────────┤
│ 2. Application Layer   (FastAPI, Python)                    │
│    Asset Mgmt, Vuln Repo, Risk Engine, Compliance Engine,   │
│    Workflow Engine, REST API Gateway, Auth/RBAC             │
├───────────────────────────────────────────────────────────┤
│ 2.5 Custom Standards & Policies Input Layer                 │
│    Upload (CSV/Excel/Word/JSON/Manual) → Normalize → Map    │
├───────────────────────────────────────────────────────────┤
│ 3. AI Layer (LangGraph + LangChain + Ollama)                 │
│    Orchestrator Agent → Asset / Risk / Compliance / Chat     │
├───────────────────────────────────────────────────────────┤
│ 4. Cyber Knowledge Graph (Neo4j) — Single Source of Truth    │
├───────────────────────────────────────────────────────────┤
│ 5. Infrastructure (Docker, PostgreSQL, Neo4j, Ollama)        │
└───────────────────────────────────────────────────────────┘
```

## 2. Component Responsibilities

| Layer | Component | Responsibility | Tech |
|---|---|---|---|
| Presentation | Web App | UI/UX for all roles | React 18, TS, MUI |
| Application | API Gateway | Routing, auth, rate-limit | FastAPI |
| Application | Auth Service | Login, JWT, RBAC | FastAPI + python-jose + passlib |
| Application | Asset Service | Inventory, classification, relationships | FastAPI + SQLAlchemy |
| Application | Risk Engine | Score & prioritize risk | FastAPI |
| Application | Compliance Engine | Framework/control mapping | FastAPI |
| Application | Workflow Engine | Task/state orchestration | FastAPI |
| Input Layer | Standards Ingestor | Parse CSV/Excel/Word/JSON, normalize, map | pandas, python-docx, openpyxl |
| AI | Orchestrator Agent | Route requests to specialist agents | LangGraph |
| AI | Asset / Risk / Compliance Agents | Domain reasoning | LangChain + Ollama |
| Data | PostgreSQL | Users, auth, config, audit logs | PostgreSQL 16 |
| Data | Neo4j | Assets, identities, risks, vulns, controls, policies, relationships | Neo4j 5 |
| Infra | Docker Compose | Local/dev orchestration of all services | Docker |

## 3. Data Flow (example: "What are my top 5 risks?")
1. User asks the AI Chat Assistant.
2. Orchestrator Agent classifies intent → routes to Risk Assessment Agent.
3. Risk Agent queries Neo4j (via Application Layer) for asset + vulnerability + control context.
4. Risk Agent scores/ranks results, passes to Chat Assistant.
5. Chat Assistant formats a natural-language response + supporting data table for the UI.

## 4. Deployment Topology (MVP / dev)

```
docker-compose.yml
 ├── frontend        (nginx serving React build)  :3000
 ├── backend         (FastAPI + Uvicorn)           :8000
 ├── postgres        (PostgreSQL 16)                :5432
 ├── neo4j           (Neo4j 5 Community)             :7474 / :7687
 └── ollama          (local LLM runtime)              :11434
```

Air-gapped ready: all services run in-network via Docker; Ollama serves models locally, no external API calls required at runtime.

## 5. Security Model
- JWT bearer tokens (access + refresh).
- RBAC enforced via FastAPI dependency (`require_role(...)`).
- Passwords hashed with bcrypt.
- Audit log table records auth events and sensitive admin actions.

## 6. Extension Points (post-MVP)
- Additional AI agents (Architecture Review, Incident Response, Threat Intelligence) plug into the same LangGraph orchestrator without touching existing agents.
- Real connectors (AD/Entra/LDAP, scanners, SIEM/EDR, cloud, ITSM) implement a common `Connector` interface (`backend/app/services/connectors/`) so mock data sources are swapped for live ones.
- Attack Path Engine consumes the same Neo4j graph; no schema migration needed to add it later.
