# Contributing to OpenDecision

Thank you for helping build a dependable decision layer for AI agents.

## Local setup

```bash
git clone https://github.com/Sunny-commit/OpenDecision.git
cd OpenDecision
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

Install `.[laya]` only when testing the real provider. Unit tests should use a fake provider and must not download model weights.

## Pull requests

1. Open or reference an issue for substantial changes.
2. Create a focused branch.
3. Add tests and documentation.
4. Run `pytest` and `ruff check .`.
5. Explain behavior and safety implications in the pull request.

## Decision packs

A decision pack should:

- solve a repeated, clearly described decision problem;
- use a typed `choice`, `score`, or `noul` question;
- define labels in precise, non-overlapping language;
- include representative evaluation examples before being advertised as production-ready;
- document calibration assumptions and failure modes;
- default to review or blocking for ambiguous consequential actions.

Do not include secrets, personal production data, or unsupported accuracy claims.

## Design principles

- Keep the core framework-agnostic.
- Keep providers behind small adapters.
- Do not present generated explanations as model evidence.
- Preserve raw provider output for debugging while exposing a stable normalized result.
- Prefer explicit contracts over hidden thresholds.
