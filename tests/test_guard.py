from opendecision import DecisionGuard


class FakeProvider:
    name = "fake"
    def __init__(self, answer): self.answer = answer
    def predict(self, state, question): return {"answer": self.answer, "raw": {"state": state}}


def test_choice_result_is_normalized():
    guard = DecisionGuard(FakeProvider({"choice": "review", "probabilities": {"allow": 0.1, "review": 0.8, "block": 0.1}}))
    result = guard.decide({"tool": "send_email"}, {"type": "choice", "instructions": "Should this action execute?", "options": {"allow": "Proceed", "review": "Review", "block": "Block"}})
    assert result.decision == "review"
    assert result.confidence == 0.8
    assert result.provider == "fake"


def test_noul_threshold_controls_boolean_decision():
    guard = DecisionGuard(FakeProvider({"noul": 0.72}))
    result = guard.decide({"command": "rm -rf /"}, {"type": "noul", "instructions": "Is this destructive?", "threshold": 0.7})
    assert result.decision is True
    assert result.probabilities == {"true": 0.72, "false": 0.28}


def test_score_is_normalized():
    guard = DecisionGuard(FakeProvider({"score": 1.5, "confidence": 0.9}))
    result = guard.decide({"ticket": "Production is unavailable"}, {"type": "score", "instructions": "How urgent is this?", "criteria": ["low", "medium", "critical"]})
    assert result.decision == 1.5
    assert result.confidence == 0.9
