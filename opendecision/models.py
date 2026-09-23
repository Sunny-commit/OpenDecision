"""Strict public data models for OpenDecision."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DecisionType = Literal["choice", "score", "noul"]
RiskLevel = Literal["low", "medium", "high", "critical"]
_OPTION_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class DecisionQuestion(BaseModel):
    """A strict typed question sent to a decision provider."""

    model_config = ConfigDict(extra="forbid")

    type: DecisionType
    instructions: str = Field(min_length=3, max_length=2000)
    options: dict[str, str] | None = None
    criteria: list[str] | dict[str, str] | None = None
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("options")
    @classmethod
    def validate_option_names(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return value
        if len(value) < 2:
            raise ValueError("choice questions require at least two options")
        for name, description in value.items():
            if not _OPTION_RE.fullmatch(name):
                raise ValueError(
                    "option names must be lowercase snake_case and at most 64 characters"
                )
            if not description.strip():
                raise ValueError(f"option {name!r} requires a description")
        return value

    @model_validator(mode="after")
    def validate_shape(self) -> DecisionQuestion:
        if self.type == "choice":
            values = self.options or self.criteria
            if not isinstance(values, dict) or len(values) < 2:
                raise ValueError("choice questions require at least two named options")
        elif self.type == "score":
            if not isinstance(self.criteria, list) or len(self.criteria) < 2:
                raise ValueError("score questions require an ordered list of at least two criteria")
            if len({item.strip().casefold() for item in self.criteria}) != len(self.criteria):
                raise ValueError("score criteria must be unique")
        elif self.options is not None or self.criteria is not None:
            raise ValueError("noul questions do not accept options or criteria")
        return self

    @classmethod
    def from_input(cls, question: DecisionQuestion | Mapping[str, Any] | str) -> DecisionQuestion:
        if isinstance(question, cls):
            return question
        if isinstance(question, str):
            return cls(type="noul", instructions=question)
        return cls.model_validate(question)

    def to_laya(self) -> dict[str, Any]:
        """Return the exact question shape expected by Laya."""
        payload: dict[str, Any] = {"type": self.type, "instructions": self.instructions}
        if self.type == "choice":
            payload["criteria"] = self.options or self.criteria
        elif self.type == "score":
            payload["criteria"] = self.criteria
        return payload


class DecisionContext(BaseModel):
    """Non-sensitive operational context attached to a decision trace."""

    model_config = ConfigDict(extra="forbid")

    actor: str | None = Field(default=None, max_length=200)
    tool: str | None = Field(default=None, max_length=200)
    action_id: str | None = Field(default=None, max_length=200)
    policy_id: str | None = Field(default=None, max_length=200)
    policy_version: str | None = Field(default=None, max_length=50)
    risk: RiskLevel = "medium"


class ProviderAttempt(BaseModel):
    provider: str
    success: bool
    latency_ms: float = Field(ge=0)
    error: str | None = None


class DecisionResult(BaseModel):
    """A normalized, auditable, provider-independent result."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    decision: str | float | bool
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    question_type: DecisionType
    provider: str
    decision_id: str
    created_at: datetime
    context_hash: str
    policy_id: str | None = None
    policy_version: str | None = None
    requires_review: bool = False
    provider_attempts: list[ProviderAttempt] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_output: Any = None

    @field_validator("probabilities")
    @classmethod
    def validate_probabilities(cls, value: dict[str, float]) -> dict[str, float]:
        for name, probability in value.items():
            if not 0.0 <= probability <= 1.0:
                raise ValueError(f"probability {name!r} must be between 0 and 1")
        if value and abs(sum(value.values()) - 1.0) > 0.05:
            raise ValueError("probabilities must sum to approximately 1")
        return value

    def matches(self, value: str | float | bool) -> bool:
        return self.decision == value
