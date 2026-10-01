from types import SimpleNamespace
from unittest.mock import Mock

from openai import BadRequestError

from decision_engine.prompt_builder import (
    LLMPromptPackage,
)

from decision_engine.providers.groq_provider import (
    GroqProvider,
)


def make_package():
    return LLMPromptPackage(
        prompt_version="1.1-test",
        system_prompt="test",
        user_payload={
            "evidence_catalog": {
                "technical.trend_alignment": (
                    "BULLISH_ALIGNED"
                ),
            },
        },
    )


def make_json_validation_error():
    response = Mock()
    response.status_code = 400
    response.headers = {}
    response.request = Mock()

    return BadRequestError(
        message="Failed to validate JSON.",
        response=response,
        body={
            "error": {
                "code": "json_validate_failed",
            },
        },
    )


def make_success_response():
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"action":"NO_TRADE"}'
                )
            )
        ]
    )


def test_retries_once_on_json_validate_failed():
    provider = GroqProvider(
        api_key="test",
        model="test-model",
        base_url="https://example.com",
    )

    create = Mock(
        side_effect=[
            make_json_validation_error(),
            make_success_response(),
        ]
    )

    provider.client.chat.completions.create = (
        create
    )

    result = provider.generate(
        make_package()
    )

    assert result == '{"action":"NO_TRADE"}'
    assert create.call_count == 2

def test_retries_only_once_when_json_validation_keeps_failing():
    provider = GroqProvider(
        api_key="test",
        model="test-model",
        base_url="https://example.com",
    )

    create = Mock(
        side_effect=[
            make_json_validation_error(),
            make_json_validation_error(),
        ]
    )

    provider.client.chat.completions.create = (
        create
    )

    try:
        provider.generate(
            make_package()
        )
    except BadRequestError:
        pass
    else:
        raise AssertionError(
            "Expected BadRequestError"
        )

    assert create.call_count == 2

def test_does_not_retry_unrelated_bad_request():
    provider = GroqProvider(
        api_key="test",
        model="test-model",
        base_url="https://example.com",
    )

    error = make_json_validation_error()
    error.code = "some_other_error"
    error.body = {
        "error": {
            "code": "some_other_error",
        },
    }

    create = Mock(
        side_effect=error
    )

    provider.client.chat.completions.create = (
        create
    )

    try:
        provider.generate(
            make_package()
        )
    except BadRequestError:
        pass
    else:
        raise AssertionError(
            "Expected BadRequestError"
        )

    assert create.call_count == 1

def test_schema_requires_exactly_four_evidence_items():
    schema = GroqProvider._build_schema(
        context_paths=[
            "technical.trend_alignment",
        ],
        evidence_values=[
            "BULLISH_ALIGNED",
        ],
    )

    evidence_schema = (
        schema["properties"]["evidence"]
    )

    assert evidence_schema["minItems"] == 4
    assert evidence_schema["maxItems"] == 4