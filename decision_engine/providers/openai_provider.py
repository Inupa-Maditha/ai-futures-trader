from __future__ import annotations

from openai import OpenAI

from decision_engine.prompt_builder import (
    LLMPromptPackage,
)


DECISION_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,

    "properties": {
        "schema_version": {
            "type": "string",
            "enum": ["1.0"],
        },

        "symbol": {
            "type": "string",
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
            "maxItems": 10,

            "items": {
                "type": "object",
                "additionalProperties": False,

                "properties": {
                    "context_path": {
                        "type": "string",
                    },

                    "value": {
                        "anyOf": [
                            {
                                "type": "string"
                            },
                            {
                                "type": "number"
                            },
                            {
                                "type": "boolean"
                            },
                            {
                                "type": "null"
                            },
                        ],
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
            },
        },

        "entry_price": {
            "anyOf": [
                {
                    "type": "number",
                    "exclusiveMinimum": 0,
                },
                {
                    "type": "null",
                },
            ],
        },

        "stop_loss": {
            "anyOf": [
                {
                    "type": "number",
                    "exclusiveMinimum": 0,
                },
                {
                    "type": "null",
                },
            ],
        },

        "take_profit": {
            "anyOf": [
                {
                    "type": "number",
                    "exclusiveMinimum": 0,
                },
                {
                    "type": "null",
                },
            ],
        },

        "invalidation_reason": {
            "anyOf": [
                {
                    "type": "string",
                },
                {
                    "type": "null",
                },
            ],
        },

        "no_trade_reason": {
            "anyOf": [
                {
                    "type": "string",
                },
                {
                    "type": "null",
                },
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
}


class OpenAIResponsesProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
    ):
        self.model = model

        self.client = OpenAI(
            api_key=api_key,
        )

    def generate(
        self,
        package: LLMPromptPackage,
    ) -> str:

        response = self.client.responses.create(
            model=self.model,

            instructions=(
                package.system_prompt
            ),

            input=package.user_json(),

            text={
                "format": {
                    "type": "json_schema",
                    "name": "decision_proposal",
                    "schema": (
                        DECISION_JSON_SCHEMA
                    ),
                    "strict": True,
                }
            },

            max_output_tokens=1200,

            # Do not persist these market
            # decision requests server-side.
            store=False,
        )

        raw_output = response.output_text

        if not raw_output:
            raise RuntimeError(
                "OpenAI returned no "
                "decision output."
            )

        return raw_output