# CSOS Phase 3 implementation provenance

Phase 3 is implemented as part of the CSOS architecture and design system.

## Reference inputs

- The customer-provided collection patch was reviewed to understand requested
  capabilities such as network CLI, SNMP, Nmap XML, Syslog and endpoint
  reporting. The collection implementation in this branch was re-authored as
  CSOS source adapters, evidence records, correlation rules, scheduling and
  secured ingestion. Stable connector names and HTTP contracts were retained
  so the portal and deployment configuration remain compatible.
- Screenshots from other cybersecurity products were used only to understand
  common operator workflows and information density. CSOS does not include
  their source code, branding, icons, visual assets or a pixel-level copy of
  their interface.
- External Python and JavaScript packages remain third-party dependencies and
  are used according to their respective licenses.

## CSOS-owned logic

The normalized evidence model, cross-source correlation, graph persistence,
finding enrichment, attack-path view, source administration, API-key security,
MCP tools, AI orchestration and CSOS portal integration are maintained as one
CSOS platform design.

Customer-specific addresses, credentials, certificates, vendor field mappings
and approved network ranges are deployment inputs and are never embedded in the
application source.
