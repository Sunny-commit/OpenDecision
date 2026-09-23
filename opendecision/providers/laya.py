from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from ..errors import ProviderError
from ..models import DecisionQuestion

class LayaProvider:
    name = "laya"
    def __init__(self, *, model: str = "router", preload: bool = True, device: str | None = None) -> None:
        self.model, self.preload, self.device, self._agent = model, preload, device, None
    def _load(self) -> Any:
        if self._agent is not None:
            return self._agent
        try:
            import laya
        except ImportError as exc:
            raise ProviderError("Laya is not installed. Install it with `pip install opendecision[laya]`.") from exc
        try:
            if self.model == "router":
                kwargs: dict[str, Any] = {"preload": self.preload}
                if self.device is not None: kwargs["device"] = self.device
                self._agent = laya.Router(**kwargs)
            else:
                kwargs = {}
                if self.device is not None: kwargs["device"] = self.device
                self._agent = laya.load("convaiinnovations/laya", subfolder=self.model, **kwargs)
        except Exception as exc:
            raise ProviderError(f"failed to load Laya model {self.model!r}: {exc}") from exc
        return self._agent
    def predict(self, state: Mapping[str, Any] | str, question: DecisionQuestion) -> Mapping[str, Any]:
        agent = self._load()
        try:
            response = agent.predict(state if isinstance(state, Mapping) else {"input": state}, {"decision": question.to_laya()})
        except Exception as exc:
            raise ProviderError(f"Laya prediction failed: {exc}") from exc
        answer = response.get("answers", {}).get("decision")
        if not isinstance(answer, Mapping):
            raise ProviderError("Laya response did not include answers.decision")
        return {"answer": answer, "raw": response, "provider": f"laya:{self.model}"}
