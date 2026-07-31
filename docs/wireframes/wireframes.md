# CSOS – UI Wireframes (Text Specification)

The platform uses a persistent role-aware navigation rail, top application bar,
and consistent design system across 12 core screens.

## 1. Login
- Center card: logo, email, password, sign-in action, error banner.

## 2. Executive Dashboard
- KPI cards: overall risk score, assets, open vulnerabilities, compliance coverage.
- Risk trend and compliance-by-framework charts.
- Top risks and recent AI insights.
- Shortcut to interactive Network Topology.

## 3. Analyst Dashboard
- Filterable investigation queue by severity, asset type, and status.
- Selected vulnerability/risk detail panel.
- Docked AI Chat Assistant and topology shortcut.

## 4. Asset Inventory
- Search and filters for type, criticality, and environment.
- Table: name, type, owner, criticality, risk score, last seen.
- Row action opens Asset Details.
- CSV/Excel import action.

## 5. Asset Details
- Header: name, type, owner, and criticality.
- Tabs: Overview | Relationships | Vulnerabilities | Compliance Controls | History.
- Relationships tab embeds an asset-centered interactive topology generated from Neo4j.

## 6. Network Topology
- Full-width interactive graph of assets, identities, vulnerabilities, risks, controls, policies, and frameworks.
- Relationship names rendered on directed edges.
- Pan, zoom, reset, search, and entity-type filters.
- Node selection opens a property detail panel.
- Metrics show visible entity and relationship counts.
- Data is generated from stored/imported Neo4j relationships; live discovery is not required.

## 7. Risk Dashboard
- Likelihood/impact heatmap.
- Prioritized risk table with score, affected asset, and recommended action.

## 8. Compliance Dashboard
- Framework selector for ISO 27001, NIST CSF, and custom frameworks.
- Coverage visualization and control-gap table.

## 9. AI Chat Assistant
- Full-page chat with conversation history.
- Inline asset/control citations and expandable agent trace.
- Model selection can be added from the configured model allow-list without changing the chat flow.

## 10. Custom Standards & Policies
- Upload zone for CSV, Excel, Word, PDF, and JSON plus manual entry.
- Parsed controls table with asset/framework mapping actions.

## 11. Reports
- Report type, format, and filter selection.
- PDF/Excel generation action and report history.

## 12. Administration
- Tabs: Users | Roles & Permissions | Audit Log | System Settings.
- AI settings can expose the provider, enabled models, and default model to authorized administrators.

## Design System

- MUI theme with primary navy (`#1E3A5F`) and accent teal (`#2FA6A6`).
- Semantic risk colors: critical `#D32F2F`, high `#F57C00`, medium `#FBC02D`, low `#43A047`.
- Topology entity colors remain consistent across the graph and details panels.
- Responsive layouts collapse control rows and detail panels on smaller screens.
