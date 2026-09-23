# Production readiness

OpenDecision is a decision-control primitive, not a complete security boundary. Deploy it behind application authentication and authorization, and preserve independent enforcement at the protected tool or service.

## Recommended decision flow

1. Validate state and a versioned decision contract.
2. Apply deterministic deny or allow rules where policy is unambiguous.
3. Use a calibrated model provider only for the residual decision space.
4. Route uncertainty and consequential actions to human review.
5. Enforce the final decision at the tool boundary.
6. Record a redacted audit event and monitor overrides and failure rates.

## Failure policy

- `raise`: fail the request and let the caller handle the outage.
- `review`: produce a human-review outcome when the contract contains one.
- `block`: deny automatically when provider output is unavailable or invalid.

Critical actions should generally use `block` or a durable review queue. The built-in in-memory review store is for prototypes and tests; production needs durable storage, authentication, RBAC, idempotency, notifications, and retention controls.

## Calibration

Tune thresholds on held-out, representative data for each policy and checkpoint. Report sample size, class balance, false positives, false negatives, Brier score, ECE, model version, hardware, and preprocessing. Never transfer thresholds between domains without evaluation.

## Audit and privacy

Built-in audit sinks store a SHA-256 context hash rather than raw state. Operators must define data classification, encryption, retention, access controls, deletion, and incident response. Do not place secrets or personal data into metadata fields.

## Risk matrix

| Risk | Default | Human review | Example |
| --- | --- | --- | --- |
| Low | allow after deterministic checks | optional | read public documentation |
| Medium | model or rules | on uncertainty | send internal notification |
| High | review | required by default | send external email or refund |
| Critical | block | explicit authorized approval | destructive command or production deletion |

## Deployment checklist

- Pin and scan dependencies.
- Protect tool credentials independently of the agent.
- Use versioned policies and immutable release artifacts.
- Run adversarial and regression fixtures.
- Configure fallback and outage behavior.
- Use a durable review service with RBAC.
- Monitor provider errors, overrides, calibration drift, and latency.
- Test rollback and emergency disable paths.
