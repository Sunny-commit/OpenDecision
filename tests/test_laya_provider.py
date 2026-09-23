import sys
from types import SimpleNamespace

import pytest

from opendecision import DecisionQuestion
from opendecision.errors import ProviderError
from opendecision.providers.laya import LayaProvider


class FakeAgent:
    def __init__(self, *, fail=False, invalid=False):
        self.fail = fail
        self.invalid = invalid

    def predict(self, state, questions):
        if self.fail:
            raise RuntimeError("prediction exploded")
        if self.invalid:
            return {"answers": {}}
        return {
            "answers": {
                "decision": {
                    "choice": "allow",
                    "probabilities": {"allow": 0.9, "block": 0.1},
                }
            },
            "routing": {"model": "english"},
        }


def question():
    return DecisionQuestion(
        type="choice",
        instructions="Should this execute?",
        options={"allow": "Proceed", "block": "Stop"},
    )


def test_router_load_is_lazy_and_cached(monkeypatch):
    calls = []

    def router(**kwargs):
        calls.append(kwargs)
        return FakeAgent()

    monkeypatch.setitem(sys.modules, "laya", SimpleNamespace(Router=router))
    provider = LayaProvider(preload=False, device="cpu")
    first = provider.predict("hello", question())
    second = provider.predict({}, question())
    assert first["provider"] == "laya:router"
    assert second["answer"]["choice"] == "allow"
    assert calls == [{"preload": False, "device": "cpu"}]


def test_named_checkpoint_and_provider_errors(monkeypatch):
    loaded = []

    def load(repo, **kwargs):
        loaded.append((repo, kwargs))
        return FakeAgent()

    monkeypatch.setitem(sys.modules, "laya", SimpleNamespace(load=load))
    provider = LayaProvider(model="typed-decisions")
    assert provider.predict({}, question())["answer"]["choice"] == "allow"
    assert loaded[0][1]["subfolder"] == "typed-decisions"

    provider._agent = FakeAgent(fail=True)
    with pytest.raises(ProviderError, match="prediction failed"):
        provider.predict({}, question())

    provider._agent = FakeAgent(invalid=True)
    with pytest.raises(ProviderError, match="answers.decision"):
        provider.predict({}, question())


def test_model_load_failure(monkeypatch):
    def router(**kwargs):
        raise RuntimeError("cannot load")

    monkeypatch.setitem(sys.modules, "laya", SimpleNamespace(Router=router))
    with pytest.raises(ProviderError, match="failed to load"):
        LayaProvider().predict({}, question())
