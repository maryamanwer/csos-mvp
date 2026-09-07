# CSOS implementation review and handover

Reviewed source: maryamanwer/csos-mvp, main snapshot 4ced646, 7 September 2026.

## What the application does

CSOS is a cybersecurity management application, not an operating system or a live network scanner. Its React interface talks to a FastAPI backend. PostgreSQL stores users, roles, authentication sessions, audit records and document metadata. Neo4j stores security assets and their relationships. Ollama supplies local language-model inference.

The existing implementation provides login and refresh tokens, user administration, asset and vulnerability CRUD/import, executive and analyst dashboards, and interactive relationship topology. The original roadmap marks Phases 1 and 2 complete; code inspection found several later-phase screens were placeholders.

## Implemented in this delivery

| Area | Previous behavior | Updated behavior |
|---|---|---|
| Chat | Fixed scaffold response | LangGraph routes to authorized asset/risk/compliance specialists, calls configured model, includes evidence IDs and traces, and stores per-user conversation history |
| Model selection | Environment configuration only | Chat model selector and runtime/installed-model status API; enabled-model validation and unavailable-runtime errors |
| Compliance | Fixed example percentages | Neo4j framework/control counts, calculated coverage, framework filtering and explicit control gaps |
| Risk assessment | Read pre-seeded risk records | New per-asset score from active vulnerability CVSS, criticality and exposure; visible formula and editable exposure |
| Reports | Returned “queued” without generating files | Real PDF/XLSX exports, persistent metadata, per-user history/downloads, literal Excel text handling and durable Compose volume |
| Standards | Read file bytes and returned “received” | Validated CSV/XLSX/JSON/Word-table and structured-text PDF parsing, control upserts, framework and asset mappings, upload history and manual entry |
| Remediation | No workflow implementation | Owner-specific tasks, validated transitions, stale-update detection, audit records and in-app notifications |
| Role bootstrap | Reset edited permission lists on restart | Preserve administrator changes when reseeding existing roles |
| Validation | 17 original tests | Added behavioral tests for the new flows and access isolation |

## Important behavior and limits

- Asset assessments use `max(active CVSS) × 10 × criticality weight × exposure weight`. Criticality weights: low .4, medium .6, high .8, critical 1. Exposure: internal .6, partner .8, internet 1. Unset exposure defaults to internal. Mitigated, accepted, false-positive, resolved and closed findings are excluded. This is a documented prioritization heuristic, not a calibrated attack probability.
- `/risk/assessments` and risk exports use calculated scores. Existing executive widgets, inventory risk labels, and `/risk/top` still use stored Risk nodes. They can differ; automated persistence/synchronization remains unfinished.
- Coverage counts implemented controls. Gap analysis additionally flags absent asset mappings. Counts concern controls actually loaded in the graph, not the complete official framework catalogs.
- Chat routing is deterministic keyword routing, with model synthesis over bounded evidence. It does not yet stream tokens, use model-driven tool planning, or validate every generated claim. Source IDs identify retrieved evidence; they do not certify model correctness. Asset evidence is limited to 100 records, risks to 5, and gaps to 100. Conversation context retains 40 messages and supplies the latest 12 to the model. Historical messages from a different access role are excluded from subsequent model context.
- Reports are synchronous. Risk reports are bounded to 5,000 assets; compliance to 1,000 frameworks; asset export supports up to 50,000 records. Report files are private to their creator.
- PDF import requires selectable text with `id | name | framework` header and pipe-separated rows. Arbitrary prose, scanned PDFs and OCR are not supported. Word import requires a table. The importer does not infer obligations or automatically certify compliance.
- Standards are validated before graph changes. Neo4j and PostgreSQL do not share one distributed transaction; a failure between systems requires checking upload history and retrying. Stable framework/control keys make graph retries upserts.
- Workflows and notifications are in-app and owner-specific. No email, Slack or external messages are sent.
- Existing endpoints primarily enforce fixed role allow-lists. Editable permission records do not yet dynamically control every route; the role editor should not be treated as a complete configurable authorization policy engine.

## Verification

36 backend tests passed, including conversation-role isolation. Backend tests use SQLite and mocked graph/model boundaries. They verify application behavior but do not prove real Neo4j Cypher execution or model quality. The frontend TypeScript check and Vite production build pass. Vite reports a large bundle warning.

Docker, live PostgreSQL, Neo4j and Ollama were not available on this host. Full Compose startup, real graph import transactions, live inference, browser end-to-end behavior, production security review, and model-family evaluation remain unverified. This delivery is not a claim that every Phase 3/4 checkbox or production acceptance requirement is complete.

## Remaining work

1. Run the full Compose integration walkthrough against real services and fix any integration failures.
2. Stream model responses; add model-driven routing/tool selection, server-side citation validation, and larger-inventory retrieval.
3. Synchronize calculated risk assessments with persisted Risk nodes and executive widgets; complete risk visualization and scoring acceptance.
4. Finish general Identity/Policy/Framework administration, advanced graph/path queries and relationship bulk imports.
5. Complete dynamic permission enforcement, production migrations, system-settings administration, monitoring and end-to-end/security tests.
6. Add arbitrary-policy extraction/OCR and human review of inferred control mappings if those formats are required.
7. Configure real scanner/directory/cloud/ITSM connectors once target systems and credentials are supplied. Requirements classify live integrations and discovery as beyond the core platform.
8. Validate chosen local models on the deployment hardware; perform stakeholder acceptance and source release.

This handover records local validation. Consult the associated pull request for repository delivery status. The supplied source excludes installed dependencies and secrets.
