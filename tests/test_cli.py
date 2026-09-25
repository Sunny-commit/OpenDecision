import json

from opendecision.cli import run


class FakeProvider:
    name = "fake"

    def __init__(self, answer):
        self.answer = answer

    def predict(self, state, question):
        return {"answer": self.answer, "raw": {"state": state}}


def test_cli_evaluate_outputs_json(capsys):
    def factory():
        from opendecision import DecisionGuard

        return DecisionGuard(FakeProvider({"choice": "allow", "confidence": 0.9}))

    exit_code = run(
        [
            "evaluate",
            "decision_packs/security/tool_risk.yaml",
            "--state",
            json.dumps({"tool": "send_email"}),
            "--json",
        ],
        guard_factory=factory,
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "allow"
    assert payload["provider"] == "fake"
