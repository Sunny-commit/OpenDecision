# OpenDecision

**A framework-agnostic decision layer for AI agents.**

OpenDecision places a typed, testable contract between an AI agent and the action it wants to take. It uses [Laya](https://github.com/NandhaKishorM/laya) for fast `choice`, `score`, and `noul` decisions without adding another text-generation step.

> Status: early MVP. Do not treat uncalibrated model confidence as a production safety guarantee.

## Why OpenDecision?

Agents repeatedly need to decide whether to continue, stop, call a tool, ask a person, retrieve more context, or escalate. OpenDecision makes those branches explicit and reusable:

- typed decision contracts instead of free-form generated text;
- normalized results across decision providers;
- community-maintained YAML decision packs;
- adapters that do not couple the core SDK to one agent framework;
- optional Laya loading, so importing OpenDecision never downloads a model.

## Install

```bash
pip install -e ".[laya]"
```

Laya and OpenDecision require Python 3.10 or newer. For the examples:

```bash
pip install -e ".[laya,langgraph,fastapi]"
```

## Quick start

```python
from opendecision import DecisionGuard

guard = DecisionGuard()
result = guard.decide(
    state={"tool": "send_email", "recipient": "customer@example.com"},
    question={
        "type": "choice",
        "instructions": "Should the agent execute this tool action?",
        "options": {
            "allow": "Proceed automatically",
            "review": "Require human approval",
            "block": "Stop the action",
        },
    },
)

print(result.decision)
print(result.probabilities)
print(result.confidence)
```

OpenDecision returns model decisions and evidence; it does **not** ask Laya to generate a reason. Applications may add an explanation separately without confusing generated prose with decision-model output.

## Decision packs

```python
from opendecision import DecisionGuard, load_policy

policy = load_policy("decision_packs/security/tool_risk.yaml")
result = DecisionGuard().decide(agent_state, policy.question)
```

The first pack includes a tool-risk contract with `allow`, `review`, and `block` outcomes.

## LangGraph

```python
from opendecision import DecisionGuard
from opendecision.integrations.langgraph import decision_node, route_by_decision

graph.add_node("tool_guard", decision_node(DecisionGuard(), question))
graph.add_conditional_edges(
    "tool_guard",
    route_by_decision(),
    {"allow": "execute_tool", "review": "human_review", "block": "stop"},
)
```

## FastAPI

```bash
uvicorn app.main:app --reload
```

Then send `POST /v1/decide` with `state` and a typed `question`.

## Architecture

```text
Agent / application
        |
DecisionGuard + contract
        |
Provider adapter (Laya first)
        |
Normalized DecisionResult
        |
ALLOW | REVIEW | BLOCK
```

## Scope of v0.1

- Python SDK and Pydantic contracts
- lazy Laya provider
- choice, score, and noul normalization
- YAML decision packs
- LangGraph node and routing helpers
- FastAPI example
- unit tests that run without downloading model weights

A dashboard, TypeScript SDK, additional frameworks, model-generated explanations, and evaluation tooling are intentionally deferred.

## Calibration and safety

Laya's documentation notes meaningful limitations: base checkpoints can be weak zero-shot on typed workflows, confidence may require domain calibration, and high-cardinality choices need special handling. Benchmark decision packs on representative data before automating consequential actions. Prefer human review when evidence or authorization is insufficient.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

Apache License 2.0. Laya is a separate Apache-2.0 project and remains subject to its own license and notices.
