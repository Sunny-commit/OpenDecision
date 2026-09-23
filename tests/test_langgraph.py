from opendecision import DecisionGuard
from opendecision.integrations.langgraph import decision_node, route_by_decision


class FakeProvider:
    name = "fake"
    def predict(self, state, question): return {"answer": {"choice": "allow", "confidence": 0.91}}


def test_langgraph_node_and_router():
    guard = DecisionGuard(FakeProvider())
    node = decision_node(guard, {"type": "choice", "instructions": "Proceed?", "options": {"allow": "Proceed", "block": "Stop"}})
    update = node({"tool": "search"})
    assert route_by_decision()({**update}) == "allow"
