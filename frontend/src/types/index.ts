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
  type: "server" | "application" | "network_device" | "database" | "cloud_resource";
  environment: string;
  criticality: Criticality;
  owner?: string;
  ip_address?: string;
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
}

export type Severity = "low" | "medium" | "high" | "critical";

export interface Vulnerability {
  id: string;
  cve_id?: string;
  title: string;
  description?: string;
  severity: Severity;
  cvss_score: number;
  status: "open" | "mitigated" | "accepted" | "false_positive";
  asset_ids: string[];
}

export interface TopologyNode {
  id: string;
  entity_id?: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface TopologyGraph {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
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
