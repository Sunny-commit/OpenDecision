"""Versioned YAML policy loading and composition."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import DecisionQuestion, RiskLevel


class DecisionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    version: str = "1.0.0"
    name: str
    description: str = ""
    risk: RiskLevel = "medium"
    default_action: Literal["allow", "review", "block"] = "review"
    question: DecisionQuestion
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def derive_legacy_id(cls, value: Any) -> Any:
        """Keep v0.1 packs valid by deriving an ID from their name."""
        if isinstance(value, dict) and not value.get("id") and value.get("name"):
            value = dict(value)
            value["id"] = str(value["name"]).strip().lower().replace(" ", "-")
        return value


def load_policy(path: str | Path) -> DecisionPolicy:
    """Load a policy and recursively compose an optional relative `extends` chain."""
    return DecisionPolicy.model_validate(_load_payload(Path(path).resolve(), set()))


def _load_payload(path: Path, seen: set[Path]) -> dict[str, Any]:
    if path in seen:
        raise ValueError(f"policy inheritance cycle detected at {path}")
    seen.add(path)
    with path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}
    extends = payload.pop("extends", None)
    if not extends:
        return payload
    base = _load_payload((path.parent / str(extends)).resolve(), seen)
    return _merge(base, payload)


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged
