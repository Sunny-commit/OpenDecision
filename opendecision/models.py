"""Public data models and input normalization for OpenDecision."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DecisionType = Literal["choice", "score", "noul"]


class DecisionQuestion(BaseModel):
    """A typed question sent to a decision provider."""
    model_config = ConfigDict(extra="allow")
    type: DecisionType
    instructions: str
    options: dict[str, str] | None = None
    criteria: list[str] | dict[str, str] | None = None
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_shape(self) -> "DecisionQuestion":
        if self.type == "choice" and not self.options and not self.criteria:
            raise ValueError("choice questions require options or criteria")
        if self.type == "score" and not self.criteria:
            raise ValueError("score questions require criteria")
        return self

    @classmethod
    def from_input(cls, question: "DecisionQuestion | Mapping[str, Any] | str") -> "DecisionQuestion":
        if isinstance(question, cls):
            return question
        if isinstance(question, str):
            return cls(type="noul", instructions=question)
        return cls.model_validate(question)

    def to_laya(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class DecisionResult(BaseModel):
    """A normalized, provider-independent decision result."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    decision: str | float | bool
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    question_type: DecisionType
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_output: Any = None

    def matches(self, value: str | float | bool) -> bool:
        return self.decision == value
