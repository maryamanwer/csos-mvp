"""Route only to authorized specialists; never execute model-generated queries."""
import json
from langgraph.graph import END, StateGraph
from app.agents.state import AgentState
from app.agents.asset_agent import asset_agent_node
from app.agents.risk_agent import risk_agent_node
from app.agents.compliance_agent import compliance_agent_node
from app.agents.chat_assistant import chat_assistant_node

def _classify_intent(state):
    q = state['user_query'].lower()
    requested = []
    if any(w in q for w in ('asset', 'server', 'network', 'database')): requested.append('asset')
    if any(w in q for w in ('risk', 'vulnerab', 'threat', 'remediat')): requested.append('risk')
    if any(w in q for w in ('complian', 'control', 'framework', 'iso', 'nist', 'policy')): requested.append('compliance')
    allowed = {'Admin': ['asset', 'risk', 'compliance'], 'Executive': ['asset', 'risk', 'compliance'],
               'Analyst': ['asset', 'risk'], 'Engineer': ['asset', 'risk'],
               'ComplianceOfficer': ['asset', 'compliance']}.get(state['user_role'], [])
    state['routes'] = [r for r in (requested or allowed) if r in allowed]
    state['agent_trace'] = ['orchestrator']
    return state

def next_node(state):
    done = state.get('completed', [])
    return next((r for r in state['routes'] if r not in done), 'answer')

def specialist(name, handler):
    def run(state):
        state = handler(state)
        state['completed'] = [*state.get('completed', []), name]
        return state
    return run

def build_orchestrator_graph():
    graph = StateGraph(AgentState)
    graph.add_node('route', _classify_intent)
    for name, fn in [('asset', asset_agent_node), ('risk', risk_agent_node), ('compliance', compliance_agent_node)]:
        graph.add_node(name, specialist(name, fn))
    graph.add_node('answer', chat_assistant_node)
    graph.set_entry_point('route')
    for name in ('route', 'asset', 'risk', 'compliance'):
        graph.add_conditional_edges(name, next_node, {n: n for n in ('asset', 'risk', 'compliance', 'answer')})
    graph.add_edge('answer', END)
    return graph.compile()

def run_orchestrator(user_query, user_role='Analyst', history=None, model=None):
    return build_orchestrator_graph().invoke({'user_query': user_query, 'user_role': user_role,
        'history': history or [], 'model': model, 'completed': [], 'retrieved_context': {}})
