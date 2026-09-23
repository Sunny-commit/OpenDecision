"""Privacy-preserving decision audit sinks."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .models import DecisionResult


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    created_at: str
    context_hash: str
    provider: str
    decision: str | float | bool
    confidence: float | None
    policy_id: str | None
    policy_version: str | None
    requires_review: bool
    actor: str | None = None
    tool: str | None = None
    action_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_result(
        cls,
        result: DecisionResult,
        *,
        actor: str | None = None,
        tool: str | None = None,
        action_id: str | None = None,
    ) -> AuditEvent:
        return cls(
            decision_id=result.decision_id,
            created_at=result.created_at.isoformat(),
            context_hash=result.context_hash,
            provider=result.provider,
            decision=result.decision,
            confidence=result.confidence,
            policy_id=result.policy_id,
            policy_version=result.policy_version,
            requires_review=result.requires_review,
            actor=actor,
            tool=tool,
            action_id=action_id,
        )


class AuditSink(Protocol):
    def write(self, event: AuditEvent) -> None: ...


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def write(self, event: AuditEvent) -> None:
        self.events.append(event)


class JsonlAuditSink:
    """Append redacted audit events; raw state and raw provider output are never written."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def write(self, event: AuditEvent) -> None:
        line = json.dumps(event.model_dump(mode="json"), sort_keys=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
