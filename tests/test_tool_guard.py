import pytest

from opendecision import DecisionGuard
from opendecision.tool_guard import ToolBlockedError, ToolReviewRequiredError, protect_tool


class FakeProvider:
    name = "fake"

    def __init__(self, answer):
        self.answer = answer

    def predict(self, state, question):
        return {"answer": self.answer, "raw": {"state": state}}


def test_protect_tool_allows_execution():
    guard = DecisionGuard(FakeProvider({"choice": "allow"}))

    @protect_tool(guard, {"type": "choice", "instructions": "?", "options": {"allow": "ok", "review": "r", "block": "b"}})
    def add(a, b):
        return a + b

    assert add(1, 2) == 3


def test_protect_tool_requests_review():
    guard = DecisionGuard(FakeProvider({"choice": "review"}))

    @protect_tool(guard, {"type": "choice", "instructions": "?", "options": {"allow": "ok", "review": "r", "block": "b"}})
    def add(a, b):
        return a + b

    with pytest.raises(ToolReviewRequiredError):
        add(1, 2)


def test_protect_tool_blocks():
    guard = DecisionGuard(FakeProvider({"choice": "block"}))

    @protect_tool(guard, {"type": "choice", "instructions": "?", "options": {"allow": "ok", "review": "r", "block": "b"}})
    def add(a, b):
        return a + b

    with pytest.raises(ToolBlockedError):
        add(1, 2)
