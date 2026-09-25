"""Command-line interface for evaluating decision packs.

Rich is an optional dependency. When available, output is rendered with tables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .guard import DecisionGuard
from .models import DecisionQuestion, DecisionResult
from .policies import load_policy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opendecision", description="Evaluate OpenDecision policies")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser(
        "evaluate",
        help="Evaluate a decision-pack YAML policy against JSON state",
    )
    evaluate.add_argument("policy", help="Path to a policy YAML file")
    evaluate.add_argument(
        "--state",
        required=True,
        help="JSON string or path to a JSON file containing agent state",
    )
    evaluate.add_argument(
        "--json",
        action="store_true",
        help="Render output as JSON (useful for scripting)",
    )

    return parser


def _load_state(value: str) -> Mapping[str, Any] | str:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _render_plain(result: DecisionResult) -> str:
    lines = [
        f"decision: {result.decision}",
        f"provider: {result.provider}",
        f"confidence: {result.confidence}",
    ]
    if result.probabilities:
        lines.append("probabilities:")
        for key, value in sorted(result.probabilities.items()):
            lines.append(f"  - {key}: {value}")
    lines.append("limitations: Model confidence is uncalibrated; prefer review when uncertain.")
    return "\n".join(lines)


def _render_rich(result: DecisionResult) -> str | None:
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        return None

    console = Console()
    table = Table(title="OpenDecision")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("decision", str(result.decision))
    table.add_row("provider", result.provider)
    table.add_row("confidence", str(result.confidence))
    console.print(table)

    if result.probabilities:
        probs = Table(title="Probabilities")
        probs.add_column("label")
        probs.add_column("p")
        for label, prob in sorted(result.probabilities.items(), key=lambda item: item[0]):
            probs.add_row(str(label), str(prob))
        console.print(probs)

    console.print(
        "[dim]limitations: Model confidence is uncalibrated; prefer review when uncertain.[/dim]"
    )
    return ""  # indicate rich rendered


def run(argv: list[str] | None = None, *, guard_factory: Callable[[], DecisionGuard] = DecisionGuard) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "evaluate":
        parser.error(f"Unknown command: {args.command}")

    policy = load_policy(args.policy)
    state = _load_state(args.state)
    guard = guard_factory()
    result = guard.decide(state, policy.question)

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    rendered = _render_rich(result)
    if rendered is None:
        print(_render_plain(result))
    return 0
