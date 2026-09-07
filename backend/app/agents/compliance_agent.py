from app.services.intelligence import coverage, gaps
def compliance_agent_node(state):
    context = state.setdefault('retrieved_context', {})
    context['coverage'] = coverage()
    context['compliance_gaps'] = gaps()[:100]
    state.setdefault('agent_trace', []).append('compliance_agent')
    return state
