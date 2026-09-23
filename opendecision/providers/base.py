"""Provider protocol used by the decision guard."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from ..models import DecisionQuestion


class DecisionProvider(Protocol):
    name: str

    def predict(
        self,
        state: Mapping[str, Any] | str,
        question: DecisionQuestion,
    ) -> Mapping[str, Any]:
        """Return a provider-native answer and optional raw response."""
