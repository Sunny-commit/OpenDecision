from pathlib import Path

from opendecision import load_policy


def test_all_bundled_policies_are_valid_and_fail_safe():
    paths = sorted(Path("decision_packs").rglob("*.yaml"))
    assert len(paths) >= 7
    policies = [load_policy(path) for path in paths]
    assert len({policy.id for policy in policies}) == len(policies)
    for policy in policies:
        assert policy.question.type in {"choice", "score", "noul"}
        if policy.risk in {"high", "critical"}:
            assert policy.default_action in {"review", "block"}
