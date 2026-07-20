# CSOS – UI Wireframes (Text Spec, Milestone 1)

10–12 MVP screens. Each entry lists layout regions and key components; visual mockups to be produced in Milestone 2 alongside implementation.

## 1. Login
- Center card: logo, email, password, "Sign in" button, error banner.

## 2. Executive Dashboard
- Top: KPI cards (Overall Risk Score, Assets, Open Vulnerabilities, Compliance %).
- Middle: Risk trend line chart (last 90 days), Compliance-by-framework bar chart.
- Right rail: Top 5 risks list, recent AI Chat insights.

## 3. Analyst Dashboard
- Left: Filterable queue (severity, asset type, status).
- Center: Selected item detail (vulnerability/risk detail panel).
- Right: AI Chat Assistant docked panel for quick queries.

## 4. Asset Inventory
- Top: search + filters (type, criticality, environment).
- Table: Name, Type, Owner, Criticality, Risk Score, Last Seen.
- Row action → Asset Details.
- "Import CSV/Excel" button top-right.

## 5. Asset Details
- Header: name, type, criticality badge.
- Tabs: Overview | Relationships (graph view) | Vulnerabilities | Compliance Controls | History.

## 6. Risk Dashboard
- Heatmap (likelihood x impact).
- Prioritized risk table with score, affected asset, recommended action.

## 7. Compliance Dashboard
- Framework selector (ISO 27001, NIST CSF, Custom).
- Coverage donut + control gap table.

## 8. AI Chat Assistant
- Full-page chat, left sidebar with conversation history.
- Inline citations to asset/control IDs; "agent trace" expandable per message.

## 9. Custom Standards & Policies
- Upload zone (CSV/Excel/Word/JSON) + manual entry form.
- Table of uploaded controls with "Map to Assets" action.

## 10. Reports
- Report type selector (Risk, Compliance, Asset).
- Filters + "Generate PDF/Excel" button; history of generated reports.

## 11. Administration
- Tabs: Users | Roles & Permissions | Audit Log | System Settings.

## 12. (Optional MVP+) Knowledge Graph Explorer
- Interactive Neo4j graph view centered on a selected asset, expandable relationships.

## Design System
- MUI theme, primary navy (#1E3A5F), accent teal (#2FA6A6), semantic risk colors (critical=#D32F2F, high=#F57C00, medium=#FBC02D, low=#43A047).
- Left persistent nav (role-aware — items hidden by RBAC), top app bar with user menu + notifications.
