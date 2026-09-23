"""Lazy Laya provider."""

from collections.abc import Mapping
from typing import Any

from ..models import DecisionQuestion


class LayaProvider:
    name = "laya"

    def __init__(self, *, model: str = "router", preload: bool = True, device: str | None = None) -> None:
        self.model = model
        self.preload = preload
        self.device = device
        self._agent: Any = None

    def _load(self) -> Any:
        if self._agent is not None:
            return self._agent
        try:
            import laya
        except ImportError as exc:
            raise RuntimeError("Laya is not installed. Install it with `pip install opendecision[laya]`.") from exc
        if self.model == "router":
            kwargs: dict[str, Any] = {"preload": self.preload}
            if self.device is not None:
                kwargs["device"] = self.device
            self._agent = laya.Router(**kwargs)
        else:
            kwargs = {}
            if self.device is not None:
                kwargs["device"] = self.device
            self._agent = laya.load("convaiinnovations/laya", subfolder=self.model, **kwargs)
        return self._agent

    def predict(self, state: Mapping[str, Any] | str, question: DecisionQuestion) -> Mapping[str, Any]:
        agent = self._load()
        state_payload = state if isinstance(state, Mapping) else {"input": state}
        response = agent.predict(state_payload, {"decision": question.to_laya()})
        answer = response.get("answers", {}).get("decision", {})
        return {"answer": answer, "raw": response}
