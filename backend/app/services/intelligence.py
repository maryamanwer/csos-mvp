"""Bounded graph intelligence and explicit, versioned risk calculation."""
from app.graph.neo4j_client import neo4j_client

def coverage():
    rows = neo4j_client.run("""
        MATCH (f:Framework)
        OPTIONAL MATCH (c:Control)-[:PART_OF]->(f)
        RETURN f.name AS framework, count(DISTINCT c) AS total_controls,
          count(DISTINCT CASE WHEN c.status = 'implemented' THEN c END) AS controls_met
        ORDER BY framework LIMIT 1000
    """)
    return [{**r, "coverage_pct": round(100 * r['controls_met'] / r['total_controls'], 1)
             if r['total_controls'] else 0} for r in rows]

def gaps(framework=None):
    return neo4j_client.run("""
        MATCH (c:Control)-[:PART_OF]->(f:Framework)
        WHERE ($framework IS NULL OR f.name = $framework)
          AND (coalesce(c.status, 'not_implemented') <> 'implemented'
               OR NOT (c)-[:APPLIES_TO]->(:Asset))
        RETURN c.id AS id, c.name AS name, f.name AS framework,
          coalesce(c.status, 'not_implemented') AS status,
          CASE WHEN NOT (c)-[:APPLIES_TO]->(:Asset) THEN 'No asset mapping'
               ELSE 'Control is not implemented' END AS reason
        ORDER BY framework, id LIMIT 1000
    """, {"framework": framework})

def score_asset(asset, vulnerabilities):
    active = [v for v in vulnerabilities if v.get('status') not in ('resolved', 'closed', 'accepted', 'mitigated', 'false_positive')]
    severity = max((float(v.get('cvss_score') if v.get('cvss_score') is not None else
                    {'critical': 10, 'high': 8, 'medium': 5, 'low': 2}.get(v.get('severity'), 0))
                    for v in active), default=0)
    criticality = {'low': .4, 'medium': .6, 'high': .8, 'critical': 1}.get(asset.get('criticality'), .6)
    exposure = {'internal': .6, 'partner': .8, 'internet': 1}.get(asset.get('exposure'), .6)
    score = round(min(100, max(0, severity * 10 * criticality * exposure)), 1)
    return {'score': score, 'likelihood': 'high' if severity >= 7 else 'medium' if severity >= 4 else 'low',
            'impact': asset.get('criticality', 'medium'),
            'explanation': f'v1: maximum active CVSS {severity} × 10 × criticality {criticality} × exposure {exposure}. Internal exposure is assumed when unset.',
            'active_vulnerabilities': len(active)}

def assessments():
    rows = neo4j_client.run("""
        MATCH (a:Asset) OPTIONAL MATCH (a)-[:HAS_VULNERABILITY]->(v:Vulnerability)
        RETURN properties(a) AS asset, collect(properties(v)) AS vulnerabilities
        ORDER BY a.id LIMIT 5000
    """)
    return sorted([{'affected_asset_id': r['asset']['id'], 'title': r['asset']['name'],
                    **score_asset(r['asset'], r['vulnerabilities'])} for r in rows],
                  key=lambda r: (-r['score'], r['affected_asset_id']))
