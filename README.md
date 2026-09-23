# OpenDecision

An auditable, typed decision layer for AI agents.

OpenDecision places explicit contracts, deterministic rules, provider fallback, human review, and privacy-preserving audit traces between an agent and consequential actions. It is a control-layer library, not a safety guarantee.

## Production-foundation preview

Version 0.2 adds:

- strict decision-contract and provider-output validation;
- deterministic rules plus ordered provider fallback chains;
- fail-safe `raise`, `review`, and `block` behavior;
- policy IDs, semantic versions, risk levels, defaults, and inheritance;
- context hashes, decision IDs, provider attempts, and JSONL audit sinks;
- an in-memory human-review workflow with loop protection;
- reproducible accuracy, confusion, and Brier-score evaluation primitives;
- coverage, lint, strict typing, and Python 3.10–3.13 CI gates.

## Example

```python
from opendecision import (
    DecisionContext,
    DecisionGuard,
    JsonlAuditSink,
    ProviderChain,
    Rule,
    RuleProvider,
)

rules = RuleProvider(
    [Rule(field="command", operator="contains", value="rm -rf", decision="block")],
)
providers = ProviderChain([rules], terminal_answer={"choice": "review"})

guard = DecisionGuard(
    providers,
    audit_sink=JsonlAuditSink("audit/decisions.jsonl"),
    failure_mode="review",
)

result = guard.decide(
    {"command": "rm -rf /tmp/cache"},
    {
        "type": "choice",
        "instructions": "Should this command execute?",
        "options": {
            "allow": "Authorized and low risk",
            "review": "Needs human approval",
            "block": "Unauthorized or destructive",
        },
    },
    context=DecisionContext(
        actor="agent:ops",
        tool="shell",
        action_id="run-123",
        policy_id="shell-command-risk",
        policy_version="1.0.0",
        risk="critical",
    ),
)
```

Raw state is hashed for correlation and is not written by the built-in audit sinks. Applications remain responsible for authentication, authorization, durable review storage, encryption, retention, monitoring, calibration, and incident response.

## Development

```bash
pip install -e ".[dev]"
coverage run -m pytest
coverage report
ruff check .
mypy opendecision
```

See `docs/production-readiness.md` for operating guidance.
