from opendecision import load_policy


def test_load_tool_risk_policy():
    policy = load_policy("decision_packs/security/tool_risk.yaml")
    assert policy.name == "tool-risk"
    assert policy.question.type == "choice"
    assert set(policy.question.options or {}) == {"allow", "review", "block"}
