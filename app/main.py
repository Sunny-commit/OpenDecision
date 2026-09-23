"""Minimal FastAPI service for OpenDecision."""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from opendecision import DecisionGuard, DecisionQuestion, DecisionResult

app = FastAPI(title="OpenDecision", version="0.1.0")
guard = DecisionGuard()


class DecisionRequest(BaseModel):
    state: dict[str, Any] | str
    question: DecisionQuestion


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/decide", response_model=DecisionResult)
def decide(request: DecisionRequest) -> DecisionResult:
    return guard.decide(request.state, request.question)
