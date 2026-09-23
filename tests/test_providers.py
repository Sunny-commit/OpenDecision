import pytest

from opendecision import DecisionQuestion, ProviderChain, Rule, RuleProvider
from opendecision.errors import ProvidersExhaustedError


class BrokenProvider:
    name = "broken"

    def predict(self, state, question):
        raise RuntimeError("unavailable")


def question():
    return DecisionQuestion(
        type="choice",
        instructions="Should this execute?",
        options={"allow": "Proceed", "review": "Review", "block": "Stop"},
    )


def test_rules_provider_supports_nested_fields():
    provider = RuleProvider(
        [
            Rule(
                field="action.command",
                operator="contains",
                value="rm -rf",
                decision="block",
            )
        ],
        default="review",
    )
    result = provider.predict({"action": {"command": "sudo rm -rf /tmp/x"}}, question())
    assert result["answer"]["choice"] == "block"


def test_chain_falls_back_and_records_attempts():
    chain = ProviderChain(
        [BrokenProvider(), RuleProvider([], default="review")],
    )
    result = chain.predict({}, question())
    assert result["provider"] == "rules"
    assert [attempt["success"] for attempt in result["attempts"]] == [False, True]


def test_terminal_fallback_and_exhaustion():
    terminal = ProviderChain([BrokenProvider()], terminal_answer={"choice": "block"})
    assert terminal.predict({}, question())["provider"] == "terminal_fallback"
    with pytest.raises(ProvidersExhaustedError):
        ProviderChain([BrokenProvider()]).predict({}, question())
