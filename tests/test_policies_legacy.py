from opendecision import load_policy


def test_v01_policy_remains_compatible():
    policy = load_policy("decision_packs/security/tool_risk.yaml")
    assert policy.id == "tool-risk"
    assert policy.version == "1.0.0"
    assert policy.question.type == "choice"
