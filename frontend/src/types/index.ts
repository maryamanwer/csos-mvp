export type Role = "Admin" | "Executive" | "Analyst" | "Engineer" | "ComplianceOfficer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at?: string;
  last_login_at?: string;
}

export type Criticality = "low" | "medium" | "high" | "critical";

export interface Asset {
  id: string;
  name: string;
  type: "server" | "application" | "network_device" | "router" | "switch" | "firewall" |
    "database" | "endpoint" | "workstation" | "cloud_resource" | "cloud" | "other";
  environment: string;
  criticality: Criticality;
  owner?: string;
  hostname?: string;
  ip_address?: string;
  operating_system?: string;
  edr_status?: "active" | "missing" | "outdated" | "not_applicable" | "unknown";
  edr_product?: string;
  edr_agent_version?: string;
  edr_agent_outdated?: boolean;
  managed_status?: "managed" | "unmanaged" | "unknown";
  data_sources?: string[];
  description?: string;
  risk_score?: number;
}

export interface Risk {
  id: string;
  title: string;
  score: number;
  likelihood: string;
  impact: string;
  status: string;
  affected_asset_id?: string;
}

export interface ComplianceCoverage {
  framework: string;
  total_controls: number;
  controls_met: number;
  coverage_pct: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  agent_trace?: string[];
  citations?: Array<{ entity_type: string; entity_id: string; label: string }>;
  created_at?: string;
}

export interface ChatConversation {
  id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
}

export type Severity = "low" | "medium" | "high" | "critical";

export interface Vulnerability {
  id: string;
  cve_id?: string;
  title: string;
  description?: string;
  severity: Severity;
  cvss_score: number;
  status: "open" | "in_progress" | "resolved" | "accepted_risk" | "mitigated" | "accepted" | "false_positive";
  first_detected?: string;
  last_seen?: string;
  sla_due_at?: string;
  recommended_remediation?: string;
  data_sources?: string[];
  asset_ids: string[];
}

export interface TopologyNode {
  id: string;
  entity_id?: string;
  label: string;
  type: string;
  asset_type?: string;
  risk_level?: "low" | "medium" | "high";
  criticality?: string;
  ip_address?: string;
  properties: Record<string, unknown>;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  category: "network" | "vulnerability" | "risk" | "identity" | "control" | "other";
  source_interface?: string;
  target_interface?: string;
  properties: Record<string, unknown>;
}

export interface TopologyGraph {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  truncated?: boolean;
}

export type FindingStatus = "open" | "in_progress" | "resolved" | "accepted_risk";
export type RiskLevel = "low" | "medium" | "high";

export interface SecurityFinding {
  finding_id: string;
  cve_id?: string;
  title: string;
  asset_id: string;
  asset_name: string;
  preferred_hostname?: string;
  asset_type: string;
  asset_criticality: string;
  asset_owner?: string;
  ip_address?: string;
  operating_system?: string;
  edr_status: string;
  edr_product?: string;
  severity: Severity;
  cvss_score: number;
  risk_score: number;
  risk_level: RiskLevel;
  status: FindingStatus;
  first_detected?: string;
  last_seen?: string;
  sla_due_at?: string;
  sla_status: "breached" | "within_sla" | "completed" | "not_set";
  sla_days_remaining?: number;
  data_sources: string[];
  recommended_remediation?: string;
  controls: Array<Record<string, unknown>>;
}

export interface FindingsSummary {
  total_findings: number;
  critical_findings: number;
  sla_breaches: number;
  critical_assets_without_edr: number;
  critical_vulnerabilities_on_critical_assets: number;
  outdated_security_agents: number;
  assets_missing_controls: number;
  unmanaged_assets: number;
}

export interface SecurityFindingsPage {
  items: SecurityFinding[];
  total: number;
  page: number;
  page_size: number;
  summary: FindingsSummary;
}

export interface FindingDetail {
  finding: SecurityFinding;
  asset: Record<string, unknown>;
  owner_identities: Array<Record<string, unknown>>;
  risks: Array<Record<string, unknown>>;
  controls: Array<Record<string, unknown>>;
  connected_assets: Array<Record<string, unknown>>;
  relationship_chain: Array<{ from: string; relationship: string; to: string }>;
}

export interface DistributionItem {
  label?: string;
  value: number;
}

export interface ExecutiveSummary {
  overall_risk_score: number;
  asset_count: number;
  open_vulnerability_count: number;
  compliance_pct: number;
  asset_criticality: DistributionItem[];
  vulnerability_severity: DistributionItem[];
  compliance_frameworks: ComplianceCoverage[];
  top_risks: Risk[];
}

export interface InvestigationItem {
  id: string;
  item_type: "risk" | "vulnerability";
  title: string;
  severity: string;
  status: string;
  priority_score: number;
  asset_ids: string[];
  reference?: string;
}

export interface RoleInfo {
  id: string;
  name: Role;
  description?: string;
  permission_codes: string[];
}

export interface AuditEntry {
  id: string;
  user_id?: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  metadata?: Record<string, unknown>;
  ip_address?: string;
  created_at: string;
}

export interface ConnectorField {
  name: string;
  label: string;
  type: "string" | "textarea" | "select" | "number" | "boolean";
  required: boolean;
  secret: boolean;
  default?: unknown;
  help?: string;
  choices?: string[];
}

export interface ConnectorType {
  key: string;
  display_name: string;
  description: string;
  category: string;
  schedulable: boolean;
  config_fields: ConnectorField[];
}

export interface ConnectorConfig {
  id: string;
  name: string;
  connector_key: string;
  description?: string;
  config: Record<string, unknown>;
  enabled: boolean;
  schedule_minutes?: number;
  last_run_at?: string;
  last_run_status?: string;
  last_run_summary?: Record<string, unknown>;
  created_at?: string;
}

export interface ConnectorRun {
  id: string;
  connector_config_id: string;
  connector_key: string;
  status: string;
  trigger: string;
  started_at?: string;
  finished_at?: string;
  duration_seconds?: number;
  assets_found: number;
  interfaces_found: number;
  links_found: number;
  vulnerabilities_found: number;
  events_found: number;
  errors?: string[];
}

export interface IngestApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scope: "agent" | "syslog";
  enabled: boolean;
  last_used_at?: string;
  use_count: number;
  created_at?: string;
  expires_at?: string;
  api_key?: string;
}

export interface AiModelStatus {
  provider: string;
  runtime: string;
  runtime_url: string;
  healthy: boolean;
  default_model: string;
  configured_models: string[];
  installed_models: string[];
  error?: string;
  air_gapped_ready: boolean;
}

export interface AttackPath {
  id: string;
  source: string;
  source_id: string;
  target: string;
  target_id: string;
  hops: number;
  score: number;
  risk_level: "medium" | "high" | "critical";
  nodes: Array<{ id: string; name: string; type?: string; criticality?: string }>;
  relationships: string[];
  vulnerabilities: Array<Record<string, unknown>>;
}
