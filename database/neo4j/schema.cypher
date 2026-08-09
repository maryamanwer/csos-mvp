// ============================================================
// CSOS Neo4j Knowledge Graph Schema (Implementation Phase 2)
// Node labels, constraints, indexes, and example relationships
// ============================================================

// ---------- Constraints (uniqueness) ----------
CREATE CONSTRAINT asset_id_unique IF NOT EXISTS
FOR (a:Asset) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT identity_id_unique IF NOT EXISTS
FOR (i:Identity) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT vulnerability_id_unique IF NOT EXISTS
FOR (v:Vulnerability) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT risk_id_unique IF NOT EXISTS
FOR (r:Risk) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT control_id_unique IF NOT EXISTS
FOR (c:Control) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT policy_id_unique IF NOT EXISTS
FOR (p:Policy) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT framework_id_unique IF NOT EXISTS
FOR (f:Framework) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT network_interface_id_unique IF NOT EXISTS
FOR (i:NetworkInterface) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT network_segment_id_unique IF NOT EXISTS
FOR (s:NetworkSegment) REQUIRE s.id IS UNIQUE;

// ---------- Indexes for common lookups ----------
CREATE INDEX asset_name_idx IF NOT EXISTS FOR (a:Asset) ON (a.name);
CREATE INDEX asset_criticality_idx IF NOT EXISTS FOR (a:Asset) ON (a.criticality);
CREATE INDEX vulnerability_severity_idx IF NOT EXISTS FOR (v:Vulnerability) ON (v.severity);
CREATE INDEX risk_score_idx IF NOT EXISTS FOR (r:Risk) ON (r.score);
CREATE INDEX asset_hostname_idx IF NOT EXISTS FOR (a:Asset) ON (a.hostname);
CREATE INDEX asset_ip_idx IF NOT EXISTS FOR (a:Asset) ON (a.ip_address);
CREATE INDEX interface_ip_idx IF NOT EXISTS FOR (i:NetworkInterface) ON (i.ip_address);

// ============================================================
// NODE MODEL (properties are illustrative; extend as needed)
// ============================================================
// (:Asset {id, name, type, environment, criticality, owner, created_at})
//     type ∈ {server, application, network_device, database, cloud_resource}
//     criticality ∈ {low, medium, high, critical}
//
// (:Identity {id, name, type, email, privileged})
//     type ∈ {user, service_account, admin}
//
// (:Vulnerability {id, cve_id, title, severity, cvss_score, status})
//     severity ∈ {low, medium, high, critical}
//     status ∈ {open, mitigated, accepted, false_positive}
//
// (:Risk {id, title, score, likelihood, impact, status, created_at})
//
// (:Control {id, name, description, source})
//     source ∈ {ISO27001, NIST_CSF, custom}
//
// (:Policy {id, name, version, uploaded_at})
//
// (:Framework {id, name, version})

// ============================================================
// RELATIONSHIP MODEL
// ============================================================
// (:Asset)-[:OWNED_BY]->(:Identity)
// (:Asset)-[:CONNECTS_TO]->(:Asset)
// (:Asset)-[:HAS_VULNERABILITY]->(:Vulnerability)
// (:Vulnerability)-[:CONTRIBUTES_TO]->(:Risk)
// (:Risk)-[:AFFECTS]->(:Asset)
// (:Control)-[:MITIGATES]->(:Risk)
// (:Control)-[:APPLIES_TO]->(:Asset)
// (:Control)-[:PART_OF]->(:Framework)
// (:Policy)-[:DEFINES]->(:Control)
// (:Identity)-[:HAS_ACCESS_TO]->(:Asset)
// (:Asset)-[:HAS_INTERFACE]->(:NetworkInterface)
// (:NetworkInterface)-[:LOCATED_IN]->(:NetworkSegment)
// Network relationships may include source_interface, target_interface,
// protocol, port, subnet, and data_sources properties when observed.

// ============================================================
// EXAMPLE SEED DATA (for local dev / demo only)
// ============================================================
MERGE (a1:Asset {id: 'asset-001'})
  SET a1.name = 'ERP-PROD-DB01', a1.type = 'database', a1.environment = 'production',
      a1.hostname = 'erp-prod-db01.csos.demo', a1.ip_address = '10.20.30.20',
      a1.criticality = 'critical', a1.owner = 'IT Infrastructure',
      a1.operating_system = 'Red Hat Enterprise Linux 9', a1.edr_status = 'active',
      a1.edr_product = 'CSOS Endpoint Sensor', a1.edr_agent_version = '8.4.2',
      a1.edr_agent_outdated = false, a1.managed_status = 'managed',
      a1.data_sources = ['CMDB', 'Vulnerability Management', 'EDR / XDR'],
      a1.created_at = datetime();

MERGE (i1:Identity {id: 'identity-001'})
  SET i1.name = 'svc-erp-db', i1.type = 'service_account', i1.privileged = true;

MERGE (v1:Vulnerability {id: 'vuln-001'})
  SET v1.cve_id = 'CVE-2024-12345', v1.title = 'Outdated TLS configuration',
      v1.severity = 'high', v1.cvss_score = 7.5, v1.status = 'open',
      v1.first_detected = datetime('2026-02-14T08:20:00Z'),
      v1.last_seen = datetime('2026-08-08T13:10:00Z'),
      v1.sla_due_at = datetime('2026-05-15T00:00:00Z'),
      v1.data_sources = ['Vulnerability Management', 'SIEM'],
      v1.recommended_remediation = 'Disable legacy TLS versions and enforce the approved cipher baseline.';

MERGE (r1:Risk {id: 'risk-001'})
  SET r1.title = 'Data exposure via weak TLS on ERP DB', r1.score = 78,
      r1.likelihood = 'medium', r1.impact = 'high', r1.status = 'open', r1.created_at = datetime();

MERGE (f1:Framework {id: 'framework-iso27001'})
  SET f1.name = 'ISO 27001', f1.version = '2022';

MERGE (c1:Control {id: 'control-a12'})
  SET c1.name = 'Cryptographic controls', c1.description = 'Use strong TLS/cipher configurations',
      c1.source = 'ISO27001', c1.status = 'implemented';

MATCH (a1:Asset {id: 'asset-001'}), (i1:Identity {id: 'identity-001'}),
      (v1:Vulnerability {id: 'vuln-001'}), (r1:Risk {id: 'risk-001'}),
      (f1:Framework {id: 'framework-iso27001'}), (c1:Control {id: 'control-a12'})
MERGE (a1)-[:OWNED_BY]->(i1)
MERGE (a1)-[:HAS_VULNERABILITY]->(v1)
MERGE (v1)-[:CONTRIBUTES_TO]->(r1)
MERGE (r1)-[:AFFECTS]->(a1)
MERGE (c1)-[:MITIGATES]->(r1)
MERGE (c1)-[:APPLIES_TO]->(a1)
MERGE (c1)-[:PART_OF]->(f1);

MERGE (a2:Asset {id: 'asset-002'})
  SET a2.name = 'CUSTOMER-PORTAL', a2.type = 'application', a2.environment = 'production',
      a2.hostname = 'portal.csos.demo', a2.ip_address = '10.20.20.15',
      a2.criticality = 'critical', a2.owner = 'Digital Services',
      a2.operating_system = 'Ubuntu Server 24.04', a2.edr_status = 'active',
      a2.edr_product = 'CSOS Endpoint Sensor', a2.edr_agent_version = '8.4.2',
      a2.edr_agent_outdated = false, a2.managed_status = 'managed',
      a2.data_sources = ['CMDB', 'Cloud platforms', 'EDR / XDR'], a2.created_at = datetime();

MERGE (a3:Asset {id: 'asset-003'})
  SET a3.name = 'EDGE-FW-01', a3.type = 'firewall', a3.environment = 'production',
      a3.hostname = 'edge-fw-01.csos.demo', a3.ip_address = '10.20.0.1',
      a3.criticality = 'critical', a3.owner = 'Network Security',
      a3.operating_system = 'Network Security OS 12.1', a3.edr_status = 'not_applicable',
      a3.edr_agent_outdated = false, a3.managed_status = 'managed',
      a3.data_sources = ['Firewall', 'Network discovery', 'SIEM'], a3.created_at = datetime();

MERGE (a4:Asset {id: 'asset-004'})
  SET a4.name = 'ANALYTICS-WORKER', a4.type = 'server', a4.environment = 'staging',
      a4.hostname = 'analytics-worker.csos.demo', a4.ip_address = '10.30.10.42',
      a4.criticality = 'medium', a4.owner = 'Data Platform',
      a4.operating_system = 'Ubuntu Server 22.04', a4.edr_status = 'outdated',
      a4.edr_product = 'CSOS Endpoint Sensor', a4.edr_agent_version = '7.8.0',
      a4.edr_agent_outdated = true, a4.managed_status = 'managed',
      a4.data_sources = ['CMDB', 'EDR / XDR'], a4.created_at = datetime();

MERGE (a5:Asset {id: 'asset-005'})
  SET a5.name = 'BACKUP-VAULT', a5.type = 'cloud_resource', a5.environment = 'production',
      a5.hostname = 'backup-vault.csos.demo', a5.ip_address = '10.40.0.18',
      a5.criticality = 'high', a5.owner = 'Infrastructure',
      a5.operating_system = 'Managed Cloud Service', a5.edr_status = 'not_applicable',
      a5.edr_agent_outdated = false, a5.managed_status = 'managed',
      a5.data_sources = ['Cloud platforms', 'CMDB'], a5.created_at = datetime();

MERGE (v2:Vulnerability {id: 'vuln-002'})
  SET v2.cve_id = 'CVE-2025-0198', v2.title = 'Public dependency with remote execution risk',
      v2.description = 'Application framework dependency requires an urgent security update.',
      v2.severity = 'critical', v2.cvss_score = 9.4, v2.status = 'in_progress',
      v2.first_detected = datetime('2026-07-01T06:30:00Z'),
      v2.last_seen = datetime('2026-08-09T01:15:00Z'),
      v2.sla_due_at = datetime('2026-08-15T00:00:00Z'),
      v2.data_sources = ['Vulnerability Management', 'Cloud platforms'],
      v2.recommended_remediation = 'Upgrade the affected framework dependency and redeploy the application image.';

MERGE (v3:Vulnerability {id: 'vuln-003'})
  SET v3.cve_id = 'CVE-2024-7781', v3.title = 'Firewall management interface exposure',
      v3.description = 'Restrict the management plane to privileged administration networks.',
      v3.severity = 'high', v3.cvss_score = 8.1, v3.status = 'open',
      v3.first_detected = datetime('2026-06-20T11:00:00Z'),
      v3.last_seen = datetime('2026-08-08T18:45:00Z'),
      v3.sla_due_at = datetime('2026-07-20T00:00:00Z'),
      v3.data_sources = ['Vulnerability Management', 'Firewall'],
      v3.recommended_remediation = 'Restrict the management interface to the privileged administration segment.';

MERGE (v4:Vulnerability {id: 'vuln-004'})
  SET v4.cve_id = null, v4.title = 'Staging server missing endpoint protection',
      v4.description = 'Deploy the approved endpoint protection baseline.',
      v4.severity = 'medium', v4.cvss_score = 5.2, v4.status = 'accepted_risk',
      v4.first_detected = datetime('2026-04-12T10:00:00Z'),
      v4.last_seen = datetime('2026-08-07T10:30:00Z'),
      v4.sla_due_at = datetime('2026-09-30T00:00:00Z'),
      v4.data_sources = ['EDR / XDR', 'CMDB'],
      v4.recommended_remediation = 'Deploy the approved endpoint protection baseline during the staging maintenance window.';

MERGE (r2:Risk {id: 'risk-002'})
  SET r2.title = 'Customer portal compromise', r2.score = 92,
      r2.likelihood = 'high', r2.impact = 'critical', r2.status = 'open', r2.created_at = datetime();

MERGE (r3:Risk {id: 'risk-003'})
  SET r3.title = 'Unauthorized firewall configuration change', r3.score = 84,
      r3.likelihood = 'medium', r3.impact = 'critical', r3.status = 'open', r3.created_at = datetime();

MERGE (r4:Risk {id: 'risk-004'})
  SET r4.title = 'Backup data availability loss', r4.score = 64,
      r4.likelihood = 'medium', r4.impact = 'high', r4.status = 'open', r4.created_at = datetime();

MERGE (f2:Framework {id: 'framework-nist-csf'})
  SET f2.name = 'NIST CSF', f2.version = '2.0';

MERGE (c2:Control {id: 'control-pr-ip-01'})
  SET c2.name = 'Platform security maintenance', c2.description = 'Apply security updates promptly',
      c2.source = 'NIST_CSF', c2.status = 'planned';

MERGE (c3:Control {id: 'control-pr-ac-01'})
  SET c3.name = 'Administrative access restriction', c3.description = 'Restrict management interfaces',
      c3.source = 'NIST_CSF', c3.status = 'implemented';

MERGE (c4:Control {id: 'control-a8'})
  SET c4.name = 'Asset lifecycle management', c4.description = 'Maintain accountable asset ownership',
      c4.source = 'ISO27001', c4.status = 'implemented';

MATCH (a1:Asset {id: 'asset-001'}), (a2:Asset {id: 'asset-002'}),
      (a3:Asset {id: 'asset-003'}), (a4:Asset {id: 'asset-004'}),
      (a5:Asset {id: 'asset-005'}),
      (v2:Vulnerability {id: 'vuln-002'}), (v3:Vulnerability {id: 'vuln-003'}),
      (v4:Vulnerability {id: 'vuln-004'}),
      (r2:Risk {id: 'risk-002'}), (r3:Risk {id: 'risk-003'}),
      (r4:Risk {id: 'risk-004'}),
      (f1:Framework {id: 'framework-iso27001'}),
      (f2:Framework {id: 'framework-nist-csf'}),
      (c2:Control {id: 'control-pr-ip-01'}),
      (c3:Control {id: 'control-pr-ac-01'}),
      (c4:Control {id: 'control-a8'})
MERGE (a2)-[:HAS_VULNERABILITY]->(v2)
MERGE (a3)-[:HAS_VULNERABILITY]->(v3)
MERGE (a4)-[:HAS_VULNERABILITY]->(v4)
MERGE (v2)-[:CONTRIBUTES_TO]->(r2)
MERGE (v3)-[:CONTRIBUTES_TO]->(r3)
MERGE (r2)-[:AFFECTS]->(a2)
MERGE (r3)-[:AFFECTS]->(a3)
MERGE (r4)-[:AFFECTS]->(a5)
MERGE (c2)-[:MITIGATES]->(r2)
MERGE (c3)-[:MITIGATES]->(r3)
MERGE (c2)-[:PART_OF]->(f2)
MERGE (c3)-[:PART_OF]->(f2)
MERGE (c4)-[:PART_OF]->(f1)
MERGE (c4)-[:APPLIES_TO]->(a2)
MERGE (a2)-[:DEPENDS_ON]->(a1)
MERGE (a2)-[:COMMUNICATES_WITH]->(a3)
MERGE (a4)-[:CONNECTS_TO]->(a5);

// Professional network and security-context demonstration topology.
MERGE (a6:Asset {id: 'asset-006'})
  SET a6.name = 'CORE-SW-01', a6.hostname = 'core-sw-01.csos.demo',
      a6.ip_address = '10.20.0.10', a6.type = 'switch', a6.environment = 'production',
      a6.criticality = 'high', a6.owner = 'Network Operations',
      a6.operating_system = 'Network Fabric OS 10.4', a6.edr_status = 'not_applicable',
      a6.edr_agent_outdated = false, a6.managed_status = 'managed',
      a6.data_sources = ['Network discovery', 'CMDB', 'SIEM'];

MERGE (a7:Asset {id: 'asset-007'})
  SET a7.name = 'WEB-PROD-01', a7.hostname = 'web-prod-01.csos.demo',
      a7.ip_address = '10.20.10.11', a7.type = 'server', a7.environment = 'production',
      a7.criticality = 'high', a7.owner = 'Digital Services',
      a7.operating_system = 'Ubuntu Server 24.04', a7.edr_status = 'active',
      a7.edr_product = 'CSOS Endpoint Sensor', a7.edr_agent_version = '8.4.2',
      a7.edr_agent_outdated = false, a7.managed_status = 'managed',
      a7.data_sources = ['EDR / XDR', 'CMDB', 'Vulnerability Management'];

MERGE (a8:Asset {id: 'asset-008'})
  SET a8.name = 'APP-PROD-01', a8.hostname = 'app-prod-01.csos.demo',
      a8.ip_address = '10.20.20.21', a8.type = 'application', a8.environment = 'production',
      a8.criticality = 'high', a8.owner = 'Application Engineering',
      a8.operating_system = 'Red Hat Enterprise Linux 9', a8.edr_status = 'active',
      a8.edr_product = 'CSOS Endpoint Sensor', a8.edr_agent_version = '8.4.1',
      a8.edr_agent_outdated = false, a8.managed_status = 'managed',
      a8.data_sources = ['EDR / XDR', 'CMDB', 'Patch Management'];

MERGE (a9:Asset {id: 'asset-009'})
  SET a9.name = 'UNKNOWN-ENDPOINT-17', a9.hostname = 'unknown-17.local',
      a9.ip_address = '10.20.40.117', a9.type = 'workstation', a9.environment = 'production',
      a9.criticality = 'medium', a9.owner = null,
      a9.operating_system = 'Unknown', a9.edr_status = 'missing',
      a9.edr_agent_outdated = false, a9.managed_status = 'unmanaged',
      a9.data_sources = ['Network discovery'];

MERGE (i2:Identity {id: 'identity-002'})
  SET i2.name = 'noura.analyst', i2.username = 'noura.analyst', i2.type = 'user',
      i2.role = 'Security Analyst', i2.email = 'noura.analyst@csos.demo', i2.privileged = true;

MERGE (v5:Vulnerability {id: 'vuln-005'})
  SET v5.cve_id = 'CVE-2026-4102', v5.title = 'Internet-facing web service remote execution',
      v5.description = 'The public web tier uses a component affected by remote code execution.',
      v5.severity = 'critical', v5.cvss_score = 9.8, v5.status = 'open',
      v5.first_detected = datetime('2026-08-01T03:45:00Z'),
      v5.last_seen = datetime('2026-08-09T02:10:00Z'),
      v5.sla_due_at = datetime('2026-08-08T00:00:00Z'),
      v5.data_sources = ['Vulnerability Management', 'EDR / XDR', 'SIEM'],
      v5.recommended_remediation = 'Apply the vendor security update and recycle the public web workload.';

MERGE (r5:Risk {id: 'risk-005'})
  SET r5.title = 'Public web tier compromise', r5.score = 96,
      r5.severity = 'high', r5.exposure = 'internet', r5.likelihood = 'high',
      r5.impact = 'critical', r5.status = 'open', r5.created_at = datetime();

MERGE (c5:Control {id: 'control-web-waf'})
  SET c5.name = 'Web application protection', c5.description = 'Protect public workloads with managed filtering.',
      c5.source = 'NIST_CSF', c5.status = 'implemented';

MERGE (internet:NetworkSegment {id: 'segment-internet'})
  SET internet.name = 'Internet', internet.zone = 'external';
MERGE (dmz:NetworkSegment {id: 'segment-dmz'})
  SET dmz.name = 'DMZ', dmz.cidr = '10.20.10.0/24', dmz.vlan = '110', dmz.zone = 'dmz';
MERGE (app_zone:NetworkSegment {id: 'segment-app'})
  SET app_zone.name = 'Application Zone', app_zone.cidr = '10.20.20.0/24',
      app_zone.vlan = '120', app_zone.zone = 'internal';
MERGE (data_zone:NetworkSegment {id: 'segment-data'})
  SET data_zone.name = 'Data Zone', data_zone.cidr = '10.20.30.0/24',
      data_zone.vlan = '130', data_zone.zone = 'restricted';
MERGE (user_zone:NetworkSegment {id: 'segment-user'})
  SET user_zone.name = 'User LAN', user_zone.cidr = '10.20.40.0/24',
      user_zone.vlan = '140', user_zone.zone = 'internal';

MERGE (if_fw_wan:NetworkInterface {id: 'if-fw-wan'})
  SET if_fw_wan.name = 'wan0', if_fw_wan.ip_address = '203.0.113.10',
      if_fw_wan.subnet = '203.0.113.0/24', if_fw_wan.interface_type = 'ethernet',
      if_fw_wan.status = 'up';
MERGE (if_fw_lan:NetworkInterface {id: 'if-fw-lan'})
  SET if_fw_lan.name = 'lan0', if_fw_lan.ip_address = '10.20.0.1',
      if_fw_lan.subnet = '10.20.0.0/24', if_fw_lan.interface_type = 'ethernet',
      if_fw_lan.status = 'up';
MERGE (if_sw_uplink:NetworkInterface {id: 'if-sw-uplink'})
  SET if_sw_uplink.name = 'Gi0/48', if_sw_uplink.ip_address = '10.20.0.10',
      if_sw_uplink.subnet = '10.20.0.0/24', if_sw_uplink.interface_type = 'ethernet',
      if_sw_uplink.status = 'up';
MERGE (if_web:NetworkInterface {id: 'if-web-eth0'})
  SET if_web.name = 'eth0', if_web.ip_address = '10.20.10.11', if_web.subnet = '10.20.10.0/24',
      if_web.vlan = '110', if_web.interface_type = 'virtual', if_web.status = 'up';
MERGE (if_app:NetworkInterface {id: 'if-app-eth0'})
  SET if_app.name = 'eth0', if_app.ip_address = '10.20.20.21', if_app.subnet = '10.20.20.0/24',
      if_app.vlan = '120', if_app.interface_type = 'virtual', if_app.status = 'up';
MERGE (if_db:NetworkInterface {id: 'if-db-eth0'})
  SET if_db.name = 'eth0', if_db.ip_address = '10.20.30.20', if_db.subnet = '10.20.30.0/24',
      if_db.vlan = '130', if_db.interface_type = 'virtual', if_db.status = 'up';
MERGE (if_user:NetworkInterface {id: 'if-user-eth0'})
  SET if_user.name = 'Ethernet', if_user.ip_address = '10.20.40.117',
      if_user.subnet = '10.20.40.0/24', if_user.vlan = '140',
      if_user.interface_type = 'ethernet', if_user.status = 'up';

MATCH (db:Asset {id: 'asset-001'}), (firewall:Asset {id: 'asset-003'}),
      (core:Asset {id: 'asset-006'}), (web:Asset {id: 'asset-007'}),
      (app:Asset {id: 'asset-008'}), (endpoint:Asset {id: 'asset-009'})
MATCH (if_fw_wan:NetworkInterface {id: 'if-fw-wan'}),
      (if_fw_lan:NetworkInterface {id: 'if-fw-lan'}),
      (if_sw_uplink:NetworkInterface {id: 'if-sw-uplink'}),
      (if_web:NetworkInterface {id: 'if-web-eth0'}),
      (if_app:NetworkInterface {id: 'if-app-eth0'}),
      (if_db:NetworkInterface {id: 'if-db-eth0'}),
      (if_user:NetworkInterface {id: 'if-user-eth0'})
MATCH (internet:NetworkSegment {id: 'segment-internet'}),
      (dmz:NetworkSegment {id: 'segment-dmz'}),
      (app_zone:NetworkSegment {id: 'segment-app'}),
      (data_zone:NetworkSegment {id: 'segment-data'}),
      (user_zone:NetworkSegment {id: 'segment-user'})
MATCH (v5:Vulnerability {id: 'vuln-005'}), (r5:Risk {id: 'risk-005'}),
      (c5:Control {id: 'control-web-waf'}), (i2:Identity {id: 'identity-002'})
MERGE (firewall)-[:HAS_INTERFACE]->(if_fw_wan)
MERGE (firewall)-[:HAS_INTERFACE]->(if_fw_lan)
MERGE (core)-[:HAS_INTERFACE]->(if_sw_uplink)
MERGE (web)-[:HAS_INTERFACE]->(if_web)
MERGE (app)-[:HAS_INTERFACE]->(if_app)
MERGE (db)-[:HAS_INTERFACE]->(if_db)
MERGE (endpoint)-[:HAS_INTERFACE]->(if_user)
MERGE (if_fw_wan)-[:LOCATED_IN]->(internet)
MERGE (if_web)-[:LOCATED_IN]->(dmz)
MERGE (if_app)-[:LOCATED_IN]->(app_zone)
MERGE (if_db)-[:LOCATED_IN]->(data_zone)
MERGE (if_user)-[:LOCATED_IN]->(user_zone)
MERGE (firewall)-[:CONNECTS_TO {source_interface: 'lan0', target_interface: 'Gi0/48',
      subnet: '10.20.0.0/24', data_sources: ['Firewall', 'Network discovery']}]->(core)
MERGE (core)-[:CONNECTS_TO {source_interface: 'Gi0/10', target_interface: 'eth0',
      vlan: '110', subnet: '10.20.10.0/24', data_sources: ['Network discovery']}]->(web)
MERGE (web)-[:DEPENDS_ON {source_interface: 'eth0', target_interface: 'eth0',
      protocol: 'HTTPS', port: 8443, data_sources: ['SIEM']}]->(app)
MERGE (app)-[:DEPENDS_ON {source_interface: 'eth0', target_interface: 'eth0',
      protocol: 'TLS', port: 5432, data_sources: ['SIEM']}]->(db)
MERGE (firewall)-[:PROTECTS {policy: 'DMZ-INBOUND'}]->(web)
MERGE (core)-[:CONNECTS_TO {source_interface: 'Gi0/20', target_interface: 'Ethernet',
      vlan: '140', data_sources: ['Network discovery']}]->(endpoint)
MERGE (web)-[:HAS_VULNERABILITY]->(v5)
MERGE (v5)-[:CONTRIBUTES_TO]->(r5)
MERGE (r5)-[:AFFECTS]->(web)
MERGE (c5)-[:MITIGATES]->(r5)
MERGE (c5)-[:APPLIES_TO]->(web)
MERGE (firewall)-[:CONNECTED_TO {source_interface: 'wan0', target_interface: 'Internet',
      data_sources: ['Firewall', 'Network discovery']}]->(internet)
MERGE (i2)-[:HAS_ACCESS_TO {access: 'privileged', source: 'Active Directory / Identity'}]->(app)
MERGE (i2)-[:ASSOCIATED_WITH {relationship: 'investigator'}]->(web);

// ============================================================
// EXAMPLE QUERIES
// ============================================================
// Top risks with affected asset and mitigating controls:
// MATCH (r:Risk)-[:AFFECTS]->(a:Asset)
// OPTIONAL MATCH (c:Control)-[:MITIGATES]->(r)
// RETURN r, a, collect(c) AS controls
// ORDER BY r.score DESC LIMIT 5;
//
// Full relationship neighborhood for one asset:
// MATCH (a:Asset {id: $assetId})-[rel]-(n)
// RETURN a, rel, n;
