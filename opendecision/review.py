from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from .errors import ReviewLoopError
from .models import DecisionResult

class ReviewStatus(str, Enum):
    pending, approved, rejected = "pending", "approved", "rejected"

class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    decision_id: str
    status: ReviewStatus = ReviewStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    reviewer: str | None = None
    reason: str | None = None
    final_decision: str | bool | float | None = None

class InMemoryReviewStore:
    def __init__(self, *, max_attempts_per_action: int = 3) -> None:
        self.max_attempts_per_action = max_attempts_per_action
        self.requests: dict[str, ReviewRequest] = {}
    def create(self, action_id: str, result: DecisionResult) -> ReviewRequest:
        if sum(item.action_id == action_id for item in self.requests.values()) >= self.max_attempts_per_action:
            raise ReviewLoopError(f"action {action_id!r} exceeded review attempt limit")
        request = ReviewRequest(action_id=action_id, decision_id=result.decision_id)
        self.requests[request.review_id] = request
        return request
    def resolve(self, review_id: str, *, approved: bool, reviewer: str, reason: str, final_decision: str | bool | float | None = None) -> ReviewRequest:
        request = self.requests[review_id]
        if request.status is not ReviewStatus.pending: raise ValueError("review request is already resolved")
        request.status = ReviewStatus.approved if approved else ReviewStatus.rejected
        request.resolved_at, request.reviewer, request.reason, request.final_decision = datetime.now(timezone.utc), reviewer, reason, final_decision
        return request
