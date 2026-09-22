from __future__ import annotations

from openai import OpenAI

from decision_engine.prompt_builder import (
    LLMPromptPackage,
)

from decision_engine.providers.openai_provider import (
    DECISION_JSON_SCHEMA,
)


class LMStudioProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
    ):
        self.model = model

        self.client = OpenAI(
            base_url=base_url,

            # LM Studio normally does not
            # require authentication.
            # OpenAI SDK expects a value.
            api_key="lm-studio",
        )

    def generate(
        self,
        package: LLMPromptPackage,
    ) -> str:

        response = (
            self.client
            .chat.completions.create(
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

                        "schema": (
                            DECISION_JSON_SCHEMA
                        ),
                    },
                },

                temperature=0.1,

                max_tokens=1200,
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
                "LM Studio returned "
                "no decision output."
            )

        return raw_output