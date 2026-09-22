from __future__ import annotations

from openai import OpenAI

from decision_engine.prompt_builder import (
    LLMPromptPackage,
)


class GroqProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
    ):
        self.model = model

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def generate(
        self,
        package: LLMPromptPackage,
    ) -> str:

        catalog = (
            package.user_payload
            .get(
                "evidence_catalog",
                {}
            )
        )

        if not catalog:
            raise RuntimeError(
                "Evidence catalog is missing "
                "from LLM prompt package."
            )

        context_paths = list(
            catalog.keys()
        )

        evidence_values = list(
            dict.fromkeys(
                catalog.values()
            )
        )

        schema = self._build_schema(
            context_paths=context_paths,
            evidence_values=evidence_values,
        )

        response = (
            self.client
            .chat.completions
            .create(
                model=self.model,

                messages=[
                    {
                        "role": "system",
                        "content": (
                            package.system_prompt
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            package.user_json()
                        ),
                    },
                ],

                response_format={
                    "type": "json_schema",

                    "json_schema": {
                        "name": (
                            "decision_proposal"
                        ),

                        "strict": True,

                        "schema": schema,
                    },
                },

                temperature=0,

                reasoning_effort="low",

                max_completion_tokens=2000,
            )
        )

        raw_output = (
            response
            .choices[0]
            .message
            .content
        )

        if not raw_output:
            raise RuntimeError(
                "Groq returned no "
                "decision output."
            )

        return raw_output

    @staticmethod
    def _build_schema(
        context_paths: list[str],
        evidence_values: list[str],
    ) -> dict:

        return {
            "type": "object",

            "properties": {
                "schema_version": {
                    "type": "string",
                    "enum": ["1.0"],
                },

                "symbol": {
                    "type": "string",
                    "enum": ["BTCUSDT"],
                },

                "action": {
                    "type": "string",
                    "enum": [
                        "LONG",
                        "SHORT",
                        "NO_TRADE",
                    ],
                },

                "setup_quality": {
                    "type": "string",
                    "enum": [
                        "HIGH",
                        "MEDIUM",
                        "LOW",
                    ],
                },

                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                },

                "thesis": {
                    "type": "string",
                },

                "evidence": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 6,

                    "items": {
                        "type": "object",

                        "properties": {
                            "context_path": {
                                "type": "string",
                                "enum": (
                                    context_paths
                                ),
                            },

                            "value": {
                                "type": "string",
                                "enum": (
                                    evidence_values
                                ),
                            },

                            "direction": {
                                "type": "string",
                                "enum": [
                                    "BULLISH",
                                    "BEARISH",
                                    "NEUTRAL",
                                ],
                            },

                            "interpretation": {
                                "type": "string",
                            },
                        },

                        "required": [
                            "context_path",
                            "value",
                            "direction",
                            "interpretation",
                        ],

                        "additionalProperties": False,
                    },
                },

                "entry_price": {
                    "type": [
                        "number",
                        "null",
                    ],
                },

                "stop_loss": {
                    "type": [
                        "number",
                        "null",
                    ],
                },

                "take_profit": {
                    "type": [
                        "number",
                        "null",
                    ],
                },

                "invalidation_reason": {
                    "type": [
                        "string",
                        "null",
                    ],
                },

                "no_trade_reason": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
            },

            "required": [
                "schema_version",
                "symbol",
                "action",
                "setup_quality",
                "confidence",
                "thesis",
                "evidence",
                "entry_price",
                "stop_loss",
                "take_profit",
                "invalidation_reason",
                "no_trade_reason",
            ],

            "additionalProperties": False,
        }