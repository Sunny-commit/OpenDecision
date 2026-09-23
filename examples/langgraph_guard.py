"""Insert OpenDecision into a LangGraph workflow."""

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from opendecision import DecisionGuard
from opendecision.integrations.langgraph import decision_node, route_by_decision


class AgentState(TypedDict, total=False):
    tool: str
    arguments: dict
    decision_result: dict


graph = StateGraph(AgentState)
graph.add_node(
    "guard",
    decision_node(
        DecisionGuard(),
        {
            "type": "choice",
            "instructions": "Should the agent execute this tool action?",
            "options": {
                "allow": "Proceed automatically",
                "review": "Require human approval",
                "block": "Stop the action",
            },
        },
    ),
)
graph.set_entry_point("guard")
graph.add_conditional_edges(
    "guard",
    route_by_decision(),
    {"allow": END, "review": END, "block": END},
)
app = graph.compile()
