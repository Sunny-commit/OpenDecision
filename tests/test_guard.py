import pytest

from opendecision import DecisionContext, DecisionGuard, MemoryAuditSink
from opendecision.errors import ContractValidationError

class FakeProvider:
    name = "fake"
    def __init__(self, answer=None, error=None): self.answer, self.error = answer, error
    def predict(self, state, question):
        if self.error: raise self.error
        return {"answer": self.answer, "raw": {"model": "fake-v1"}}

def choice_question():
    return {"type":"choice","instructions":"Should this action execute?","options":{"allow":"Proceed","review":"Review","block":"Stop"}}

def test_choice_normalizes_and_audits_without_raw_state():
    sink = MemoryAuditSink()
    guard = DecisionGuard(FakeProvider({"choice":"review","probabilities":{"allow":0.1,"review":0.8,"block":0.1}}), audit_sink=sink)
    result = guard.decide({"secret":"do-not-log","tool":"send_email"}, choice_question(), context=DecisionContext(actor="user-1",tool="send_email",policy_id="tool-risk",policy_version="1.0.0"))
    assert result.decision == "review" and result.requires_review
    assert len(result.context_hash) == 64 and sink.events[0].actor == "user-1"
    assert "secret" not in sink.events[0].model_dump_json()

def test_invalid_choice_output_is_rejected():
    with pytest.raises(ContractValidationError, match="not one of"):
        DecisionGuard(FakeProvider({"choice":"invented"})).decide({"tool":"x"}, choice_question())

def test_invalid_state_is_rejected_before_provider():
    with pytest.raises(ContractValidationError, match="JSON serializable"):
        DecisionGuard(FakeProvider({"noul":0.5})).check({"bad":object()}, decision="Is this risky?")

def test_failure_modes_review_and_block():
    provider = FakeProvider(error=RuntimeError("down"))
    review = DecisionGuard(provider,failure_mode="review").decide({},choice_question())
    block = DecisionGuard(provider,failure_mode="block").decide({},choice_question())
    assert review.decision == "review" and review.requires_review
    assert block.decision == "block" and not block.requires_review

def test_noul_and_score_normalization():
    noul=DecisionGuard(FakeProvider({"noul":0.75})).check({},decision="Risky?")
    score=DecisionGuard(FakeProvider({"score":1.5,"confidence":0.9})).decide({}, {"type":"score","instructions":"How urgent is this?","criteria":["low","high"]})
    assert noul.decision is True and score.decision == 1.5
