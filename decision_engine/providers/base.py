from __future__ import annotations

from typing import Protocol

from decision_engine.prompt_builder import (
    LLMPromptPackage,
)


class LLMProvider(Protocol):
    def generate(
        self,
        package: LLMPromptPackage,
    ) -> str:
        ...