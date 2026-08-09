# CSOS – Implementation Phase 2 Release Notes

## Release status

Implementation Phase 2 – Core Platform Development is complete. The delivered
platform replaces the Phase 1 demonstration stubs in the authentication,
administration, dashboard, asset, relationship, and vulnerability workflows
with persistent PostgreSQL and Neo4j services.

## Delivered capabilities

| Capability | Delivered behavior |
|---|---|
| Authentication | PostgreSQL user lookup, bcrypt password verification, access and refresh JWTs, refresh rotation, replay protection, logout revocation, and current-user restoration |
| RBAC | Seeded Admin, Executive, Analyst, Engineer, and Compliance Officer roles with permission mappings and protected API/UI routes |
| Administration | User creation, profile/role/status updates, role permission visibility and updates, and paginated audit history |
| Executive Dashboard | Overall risk, asset count, open vulnerabilities, compliance coverage, criticality/severity distributions, framework coverage, and top risks |
| Analyst Dashboard | Prioritized investigation queue combining risk, asset, vulnerability, and relationship context |
| Asset Inventory | Search, filters, create, edit, deactivate/delete, classification, CSV/XLSX import, details, and connected-vulnerability context |
| Asset relationships | Neo4j relationship creation/removal and focused topology exploration from Asset Details |
| Vulnerability Repository | Search, severity/status filters, create, edit, delete, CSV/XLSX import, and asset linking |
| Security Findings | Correlated asset/finding table, security-gap KPIs, advanced filters, saved views, sorting, pagination, CSV export, and investigation drill-down |
| Network/security topology | Semantic network layers, interface/IP/VLAN labels, security relationships, risk colors, filters, and connected-context highlighting |
| Auditability | Authentication, user administration, asset, relationship, and vulnerability changes recorded in PostgreSQL |

## Demonstration data

The Neo4j initialization script now creates a connected security dataset with
nine assets, five vulnerabilities, five risks, compliance frameworks, controls,
identities, network segments, interfaces, and their relationships. Dashboard,
findings, and topology screens therefore display meaningful data immediately
after a new Docker volume is initialized.

The PostgreSQL bootstrap creates roles, permissions, and the documented local
administrator account idempotently. These values are development defaults and
must be changed for a production deployment.

## Bulk import templates

- `docs/samples/assets-import.csv`
- `docs/samples/vulnerabilities-import.csv`

Uploads are limited by `MAX_IMPORT_ROWS` and validated before data is written.

## Verification

- Backend: 19 automated tests passing
- Frontend: topology layout, filtering, and risk-color tests passing
- Frontend: TypeScript project build passing
- Frontend: Vite production build passing
- Repository: Python source compilation and Git whitespace validation passing

## Deferred scope

Model-driven agent reasoning, grounded AI streaming, advanced graph path
analytics, report generation, standards parsing, and workflow automation remain
scheduled in Implementation Phases 3 and 4.
