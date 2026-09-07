from app.graph.neo4j_client import neo4j_client
def asset_agent_node(state):
    # Retrieve bounded inventory; relevance is resolved by the answer model.
    state.setdefault('retrieved_context', {})['assets'] = neo4j_client.list_assets(limit=100)
    state.setdefault('agent_trace', []).append('asset_intelligence_agent')
    return state
