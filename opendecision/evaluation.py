"""Small reproducible evaluation primitives for decision packs."""

from __future__ import annotations
from collections import Counter
from pydantic import BaseModel, ConfigDict, Field

class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    expected: str
    predicted: str
    probabilities: dict[str, float] = Field(default_factory=dict)

class EvaluationReport(BaseModel):
    total: int
    correct: int
    accuracy: float
    brier_score: float | None
    confusion: dict[str, int]

def evaluate(cases: list[EvaluationCase]) -> EvaluationReport:
    if not cases:
        raise ValueError("at least one evaluation case is required")
    correct = sum(case.expected == case.predicted for case in cases)
    confusion = Counter(f"{case.expected}->{case.predicted}" for case in cases)
    brier_values: list[float] = []
    for case in cases:
        if case.probabilities:
            labels = set(case.probabilities) | {case.expected}
            brier_values.append(sum((case.probabilities.get(label, 0.0) - (1.0 if label == case.expected else 0.0)) ** 2 for label in labels) / len(labels))
    return EvaluationReport(total=len(cases), correct=correct, accuracy=correct / len(cases), brier_score=(sum(brier_values) / len(brier_values) if brier_values else None), confusion=dict(confusion))
