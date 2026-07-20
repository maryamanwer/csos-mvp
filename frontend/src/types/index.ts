export type Role = "Admin" | "Executive" | "Analyst" | "Engineer" | "ComplianceOfficer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export type Criticality = "low" | "medium" | "high" | "critical";

export interface Asset {
  id: string;
  name: string;
  type: "server" | "application" | "network_device" | "database" | "cloud_resource";
  environment: string;
  criticality: Criticality;
  owner?: string;
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
