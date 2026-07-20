// ============================================================
// CSOS Neo4j Knowledge Graph Schema (Milestone 1)
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
      c1.source = 'ISO27001';

MERGE (a1)-[:OWNED_BY]->(i1)
MERGE (a1)-[:HAS_VULNERABILITY]->(v1)
MERGE (v1)-[:CONTRIBUTES_TO]->(r1)
MERGE (r1)-[:AFFECTS]->(a1)
MERGE (c1)-[:MITIGATES]->(r1)
MERGE (c1)-[:APPLIES_TO]->(a1)
MERGE (c1)-[:PART_OF]->(f1);

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
