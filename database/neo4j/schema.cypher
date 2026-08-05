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

// ---------- Indexes for common lookups ----------
CREATE INDEX asset_name_idx IF NOT EXISTS FOR (a:Asset) ON (a.name);
CREATE INDEX asset_criticality_idx IF NOT EXISTS FOR (a:Asset) ON (a.criticality);
CREATE INDEX vulnerability_severity_idx IF NOT EXISTS FOR (v:Vulnerability) ON (v.severity);
CREATE INDEX risk_score_idx IF NOT EXISTS FOR (r:Risk) ON (r.score);

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

// ============================================================
// EXAMPLE SEED DATA (for local dev / demo only)
// ============================================================
MERGE (a1:Asset {id: 'asset-001'})
  SET a1.name = 'ERP-PROD-DB01', a1.type = 'database', a1.environment = 'production',
      a1.criticality = 'critical', a1.owner = 'IT Infrastructure', a1.created_at = datetime();

MERGE (i1:Identity {id: 'identity-001'})
  SET i1.name = 'svc-erp-db', i1.type = 'service_account', i1.privileged = true;

MERGE (v1:Vulnerability {id: 'vuln-001'})
  SET v1.cve_id = 'CVE-2024-12345', v1.title = 'Outdated TLS configuration',
      v1.severity = 'high', v1.cvss_score = 7.5, v1.status = 'open';

MERGE (r1:Risk {id: 'risk-001'})
  SET r1.title = 'Data exposure via weak TLS on ERP DB', r1.score = 78,
      r1.likelihood = 'medium', r1.impact = 'high', r1.status = 'open', r1.created_at = datetime();

MERGE (f1:Framework {id: 'framework-iso27001'})
  SET f1.name = 'ISO 27001', f1.version = '2022';

MERGE (c1:Control {id: 'control-a12'})
  SET c1.name = 'Cryptographic controls', c1.description = 'Use strong TLS/cipher configurations',
      c1.source = 'ISO27001', c1.status = 'implemented';

MERGE (a1)-[:OWNED_BY]->(i1)
MERGE (a1)-[:HAS_VULNERABILITY]->(v1)
MERGE (v1)-[:CONTRIBUTES_TO]->(r1)
MERGE (r1)-[:AFFECTS]->(a1)
MERGE (c1)-[:MITIGATES]->(r1)
MERGE (c1)-[:APPLIES_TO]->(a1)
MERGE (c1)-[:PART_OF]->(f1);

MERGE (a2:Asset {id: 'asset-002'})
  SET a2.name = 'CUSTOMER-PORTAL', a2.type = 'application', a2.environment = 'production',
      a2.criticality = 'high', a2.owner = 'Digital Services', a2.created_at = datetime();

MERGE (a3:Asset {id: 'asset-003'})
  SET a3.name = 'EDGE-FW-01', a3.type = 'network_device', a3.environment = 'production',
      a3.criticality = 'critical', a3.owner = 'Network Security', a3.created_at = datetime();

MERGE (a4:Asset {id: 'asset-004'})
  SET a4.name = 'ANALYTICS-WORKER', a4.type = 'server', a4.environment = 'staging',
      a4.criticality = 'medium', a4.owner = 'Data Platform', a4.created_at = datetime();

MERGE (a5:Asset {id: 'asset-005'})
  SET a5.name = 'BACKUP-VAULT', a5.type = 'cloud_resource', a5.environment = 'production',
      a5.criticality = 'high', a5.owner = 'Infrastructure', a5.created_at = datetime();

MERGE (v2:Vulnerability {id: 'vuln-002'})
  SET v2.cve_id = 'CVE-2025-0198', v2.title = 'Public dependency with remote execution risk',
      v2.description = 'Application framework dependency requires an urgent security update.',
      v2.severity = 'critical', v2.cvss_score = 9.4, v2.status = 'open';

MERGE (v3:Vulnerability {id: 'vuln-003'})
  SET v3.cve_id = 'CVE-2024-7781', v3.title = 'Firewall management interface exposure',
      v3.description = 'Restrict the management plane to privileged administration networks.',
      v3.severity = 'high', v3.cvss_score = 8.1, v3.status = 'open';

MERGE (v4:Vulnerability {id: 'vuln-004'})
  SET v4.cve_id = null, v4.title = 'Staging server missing endpoint protection',
      v4.description = 'Deploy the approved endpoint protection baseline.',
      v4.severity = 'medium', v4.cvss_score = 5.2, v4.status = 'accepted';

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
