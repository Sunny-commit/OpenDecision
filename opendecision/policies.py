"""Small YAML-backed decision-pack loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from .models import DecisionQuestion


class DecisionPolicy(BaseModel):
    """A named, reviewable decision contract stored in a decision pack."""

    name: str
    description: str = ""
    question: DecisionQuestion
    tags: list[str] = Field(default_factory=list)


def load_policy(path: str | Path) -> DecisionPolicy:
    """Load a policy from a YAML file."""
    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}
    return DecisionPolicy.model_validate(payload)
