# CSOS Initial Release Client Acceptance

This checklist maps the agreed initial-release scope to a repeatable client
demonstration. It does not include the live enterprise integrations and advanced
operations assigned to later roadmap phases.

## Acceptance environment

1. Create a GitHub Codespace with at least 4 cores and 16 GB RAM.
2. Run `docker compose up --build -d`.
3. Run `docker compose exec ollama ollama pull llama3.1`.
4. Confirm `docker compose ps` reports healthy PostgreSQL, Neo4j and backend services.
5. Open the private forwarded port 3000 and sign in as the development administrator.

## Functional acceptance

- [ ] Create users for Executive, Analyst, Engineer, Security Architect and Compliance Officer roles.
- [ ] Change a non-administrator permission and confirm the API denies the removed capability.
- [ ] Create server, application, network, identity, database and cloud assets with environment, criticality and data sensitivity.
- [ ] Import asset and relationship samples and confirm the Neo4j topology updates.
- [ ] Create and import vulnerabilities linked to assets.
- [ ] Confirm Risk Dashboard and Executive Dashboard show the same calculated top risks.
- [ ] Review built-in NIST CSF 2.0 and CIS Controls v8 families.
- [ ] Upload a custom standard and map controls to assets.
- [ ] Confirm compliance coverage and gap reasons update from graph data.
- [ ] Ask asset, risk and compliance questions and inspect evidence IDs and agent traces.
- [ ] Generate and download PDF and Excel reports.
- [ ] Progress a remediation workflow from open through closed and inspect its audit trail and notification.
- [ ] Review non-secret effective settings and audit events in Administration.

## Operational acceptance

- [ ] Restart the Codespace/Compose stack and confirm PostgreSQL, Neo4j, reports and Ollama data persist.
- [ ] Confirm unauthenticated requests return 401 and role/permission violations return 403.
- [ ] Confirm each user can access only their own report, conversation and workflow history.
- [ ] Replace demonstration secrets and passwords before any production or public deployment.

## Deferred roadmap scope

Live AD/Entra/LDAP, SIEM, EDR, scanner, ServiceNow, cloud and ITSM connectors;
automated discovery and topology synchronization; attack-path automation;
high availability; Kubernetes; mobile clients; OCR for scanned policies; and
advanced production monitoring remain separately planned capabilities.
