from pathlib import Path

import pytest

from opendecision import (
    DecisionGuard,
    EvaluationCase,
    InMemoryReviewStore,
    JsonlAuditSink,
    RuleProvider,
    evaluate,
    load_policy,
)
from opendecision.errors import ReviewLoopError


class FakeProvider:
    name = "fake"

    def predict(self, state, question):
        return {
            "answer": {
                "choice": "review",
                "probabilities": {"allow": 0.1, "review": 0.8, "block": 0.1},
            }
        }


def test_policy_inheritance(tmp_path: Path):
    (tmp_path / "base.yaml").write_text(
        """id: base
version: 1.0.0
name: Base
risk: high
default_action: block
question:
  type: choice
  instructions: Should this action run?
  options:
    allow: Proceed
    review: Human review
    block: Stop
"""
    )
    (tmp_path / "child.yaml").write_text(
        """extends: base.yaml
id: child
version: 1.1.0
name: Child
description: Specialized policy
"""
    )
    policy = load_policy(tmp_path / "child.yaml")
    assert policy.id == "child"
    assert policy.risk == "high"
    assert policy.question.options["block"] == "Stop"


def test_policy_cycle_is_rejected(tmp_path: Path):
    (tmp_path / "a.yaml").write_text("extends: b.yaml\n")
    (tmp_path / "b.yaml").write_text("extends: a.yaml\n")
    with pytest.raises(ValueError, match="cycle"):
        load_policy(tmp_path / "a.yaml")


def test_review_lifecycle_and_loop_guard():
    result = DecisionGuard(FakeProvider()).decide(
        {},
        {
            "type": "choice",
            "instructions": "Should this execute?",
            "options": {"allow": "Proceed", "review": "Review", "block": "Stop"},
        },
    )
    store = InMemoryReviewStore(max_attempts_per_action=1)
    request = store.create("action-1", result)
    resolved = store.resolve(
        request.review_id,
        approved=False,
        reviewer="security@example.com",
        reason="Missing authorization",
        final_decision="block",
    )
    assert resolved.status.value == "rejected"
    with pytest.raises(ReviewLoopError):
        store.create("action-1", result)


def test_jsonl_audit_and_evaluation(tmp_path: Path):
    sink = JsonlAuditSink(tmp_path / "audit.jsonl")
    DecisionGuard(RuleProvider([], default="review"), audit_sink=sink).decide(
        {},
        {
            "type": "choice",
            "instructions": "Should this execute?",
            "options": {"allow": "Proceed", "review": "Review", "block": "Stop"},
        },
    )
    assert "context_hash" in (tmp_path / "audit.jsonl").read_text()
    report = evaluate(
        [
            EvaluationCase(
                case_id="1",
                expected="block",
                predicted="block",
                probabilities={"allow": 0.1, "block": 0.9},
            ),
            EvaluationCase(case_id="2", expected="allow", predicted="block"),
        ]
    )
    assert report.accuracy == 0.5
    assert report.brier_score is not None
    with pytest.raises(ValueError):
        evaluate([])
