# CSOS – Requirements Specification

## 1. Purpose

Define the business-aligned functional and non-functional requirements for the
Cyber Security Operating System (CSOS). This specification is the baseline for
the platform architecture and implementation roadmap.

## 2. User Roles

| Role | Description | Primary Screens |
|---|---|---|
| CISO / Executive | Strategic oversight, KPIs, risk trends | Executive Dashboard, Security Findings, Network Topology, Reports |
| Security Architect | Designs controls and reviews relationships | Asset Inventory, Security Findings, Network Topology, Knowledge Graph |
| Security Analyst | Investigates, triages, responds | Analyst Dashboard, Security Findings, Interactive Topology, AI Chat |
| Security Engineer | Implements controls and manages assets | Asset Inventory, Asset Details, Network Topology |
| Compliance Officer | Manages frameworks and audits | Compliance Dashboard, Custom Standards, Topology |
| Administrator | Manages users, roles, and system settings | Administration Portal |

## 3. Functional Requirements

### FR-1 Authentication & RBAC
- FR-1.1 Users authenticate through username/password and receive access/refresh JWTs.
- FR-1.2 Roles include Admin, Executive, Analyst, Engineer, and Compliance Officer.
- FR-1.3 Protected API endpoints enforce role-based authorization.

### FR-2 Asset Management
- FR-2.1 Create, read, update, and delete servers, applications, network devices, identities, databases, and cloud resources.
- FR-2.2 Classify assets by criticality, data sensitivity, and environment.
- FR-2.3 Store and query asset relationships through the Cyber Knowledge Graph.
- FR-2.4 Import assets and relationships from CSV/Excel sources.

### FR-3 Vulnerability Repository
- FR-3.1 Store vulnerabilities linked to assets, including CVE ID, severity, and status.
- FR-3.2 Support manual entry and CSV import. Live scanner integrations are planned separately.

### FR-4 Risk Engine
- FR-4.1 Compute an explainable risk score per asset from severity, exposure, and criticality.
- FR-4.2 Present a prioritized risk list and likelihood/impact view.

### FR-5 Compliance Engine
- FR-5.1 Map controls to ISO 27001, NIST CSF, and custom standards.
- FR-5.2 Present framework coverage and control gaps.

### FR-6 Custom Standards & Policies
- FR-6.1 Upload standards/policies as PDF, Excel, Word, CSV, or JSON.
- FR-6.2 Support manual entry of controls and checklist items.
- FR-6.3 Map uploaded controls to assets and frameworks.

### FR-7 Provider-Independent AI Layer
- FR-7.1 Orchestrate Asset Intelligence, Risk Assessment, Compliance, and Chat Assistant agents through LangGraph.
- FR-7.2 Use a shared agent state graph for routing, grounding, and explainability.
- FR-7.3 Use Ollama as the default local inference runtime.
- FR-7.4 Select compatible models through configuration rather than agent code. Supported examples include Llama, DeepSeek, Qwen, Mistral, ALLAM, HUMAIN-compatible models, and future sovereign/open models.
- FR-7.5 Allow a model or provider adapter to be added or switched without restructuring the application or agent architecture.

### FR-8 Cyber Knowledge Graph
- FR-8.1 Store assets, identities, vulnerabilities, risks, controls, policies, frameworks, and their relationships in Neo4j.
- FR-8.2 Expose graph queries through REST APIs for the UI and AI agents.

### FR-9 Interactive Network Topology
- FR-9.1 Generate the topology automatically from entities and relationships stored in Neo4j or imported data.
- FR-9.2 Visualize assets, identities, vulnerabilities, risks, controls, policies, frameworks, and relationship types.
- FR-9.3 Support pan, zoom, search, entity-type filtering, node selection, and relationship exploration.
- FR-9.4 Provide a full topology workspace and an asset-centered relationship view.
- FR-9.5 Do not require live network discovery; live discovery and topology synchronization are future integration capabilities.
- FR-9.6 Represent stored interface names, addresses, VLANs, subnets, and edge protocol/port metadata without inventing unavailable values.
- FR-9.7 Use the highest related asset risk for the primary red/high, orange/medium, or green/low visual state while preserving detailed risks.
- FR-9.8 Highlight a selected entity's direct investigation neighborhood and dim unrelated graph elements.

### FR-10 Reporting
- FR-10.1 Generate PDF/Excel exports for risk, compliance, and asset reports.

### FR-11 Administration
- FR-11.1 Provide user management, role assignment, audit logs, and system settings.

### FR-12 Correlated Security Findings
- FR-12.1 Present one unified asset/finding view with CVE, asset identity and ownership, IP/OS, EDR coverage, severity/CVSS, risk, status, detection dates, SLA, data sources, and remediation.
- FR-12.2 Support search, multi-dimensional advanced filters, sortable columns, pagination, saved views, and bounded CSV export.
- FR-12.3 Provide finding drill-down across Asset → Owner → Vulnerability → Security Controls → Risk → Remediation and link to the asset record.
- FR-12.4 Identify critical assets without EDR, critical vulnerabilities on critical assets, outdated agents, missing controls, unknown assets, and overdue findings.
- FR-12.5 Correlate normalized observations across available source adapters instead of presenting unrelated duplicate tool records.
- FR-12.6 Keep the query and UI contracts extensible for authorized AI agents, an MCP integration gateway, and additional Cyber Knowledge Graph connectors.

## 4. Non-Functional Requirements

- NFR-1 Deploy through Docker Compose for local environments and support air-gapped operation with no mandatory external runtime calls.
- NFR-2 Document REST APIs through OpenAPI/Swagger.
- NFR-3 Hash stored passwords with bcrypt and expire/rotate access and refresh tokens.
- NFR-4 Containerize frontend, backend, PostgreSQL, Neo4j, and Ollama independently.
- NFR-5 Keep the codebase extensible so models, providers, agents, connectors, and visual entity types can be added without core rewrites.
- NFR-6 Keep graph responses bounded and validate all externally supplied query parameters.
- NFR-7 Provide automated tests for the core application scaffold and topology projection.
- NFR-8 Apply server-side pagination, bounded exports, allow-listed sorting, and bounded graph projections to security-operations views.

## 5. Planned Beyond the Core Platform

Live AD/Entra/LDAP, SIEM, EDR, vulnerability scanner, cloud, and ITSM
connectors; high availability/clustering; mobile clients; automated discovery;
live topology synchronization; and automated attack-path generation.

## 6. Phase 1 Delivery Readiness

- [x] Requirements specification drafted and aligned to current client feedback
- [x] Solution architecture and topology data flow documented
- [x] PostgreSQL and Neo4j schemas drafted
- [x] Provider-independent AI agent architecture documented and scaffolded
- [x] UI wireframes include Network Topology as a core screen
- [x] Implementation roadmap documented without commercial pricing
- [x] Runnable repository scaffold created with local configuration template
- [x] Topology API/UI foundation implemented and covered by automated tests

Stakeholder approval is an external governance action and is not represented as
an implementation checkbox in the repository.
