import re
from pathlib import Path


def test_demo_relationship_statements_rebind_seed_entities():
    schema_path = Path(__file__).parents[2] / "database" / "neo4j" / "schema.cypher"
    schema = re.sub(r"//.*", "", schema_path.read_text(encoding="utf-8"))
    relationship_statements = [
        statement
        for statement in schema.split(";")
        if re.search(r"MERGE\s+\([A-Za-z_]\w*\)-\[:", statement)
    ]

    assert relationship_statements
    assert all(re.search(r"\bMATCH\s+\(", statement) for statement in relationship_statements)
