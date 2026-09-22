from __future__ import annotations

from collections import Counter
from statistics import mean, median
from time import perf_counter, sleep

from config.settings import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    validate_groq_settings,
)

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.llm_service import (
    LLMDecisionService,
)

from decision_engine.pipeline import (
    DecisionPipeline,
)

from decision_engine.providers.groq_provider import (
    GroqProvider,
)

from decision_engine.validator import (
    DecisionValidator,
)

from market_data.runner import (
    MarketDataRunner,
)


WARMUP_RUNS = 1
MEASURED_RUNS = 5

# Benchmark only.
# Production default remains unchanged.
BENCHMARK_MAX_CONTEXT_AGE_SECONDS = 300


def classify_result(result) -> str:
    if result.accepted:
        return "ACCEPTED"

    if result.proposal is None:
        error = (
            result.error or ""
        ).lower()

        if "provider failure" in error:
            return "PROVIDER_FAIL"

        if (
            "decisionproposal validation"
            in error
            or "not valid json"
            in error
        ):
            return "SCHEMA_OR_PARSE_FAIL"

        return "NO_PROPOSAL"

    if result.validation is not None:
        reasons = " ".join(
            result.validation.reasons
        ).lower()

        if (
            "unsupported context path"
            in reasons
            or "value mismatch"
            in reasons
        ):
            return "GROUNDING_FAIL"

        if "stale" in reasons:
            return "STALE_CONTEXT"

        return "VALIDATION_FAIL"

    return "REJECTED"


def build_service():
    provider = GroqProvider(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        base_url=GROQ_BASE_URL,
    )

    validator = DecisionValidator(
        max_context_age_seconds=(
            BENCHMARK_MAX_CONTEXT_AGE_SECONDS
        )
    )

    pipeline = DecisionPipeline(
        validator=validator,
    )

    return LLMDecisionService(
        provider=provider,
        pipeline=pipeline,
    )


def run_once(
    service,
    context,
):
    start = perf_counter()

    result = service.decide(
        context
    )

    elapsed = (
        perf_counter() - start
    )

    return result, elapsed


def print_run(
    run_number: int,
    result,
    elapsed: float,
):
    category = classify_result(
        result
    )

    print(
        "\n"
        + "-" * 60
    )

    print(
        f"Run {run_number}"
    )

    print(
        f"Time: {elapsed:.2f}s"
    )

    print(
        f"Result: {category}"
    )

    if result.error:
        print(
            f"Error: {result.error}"
        )

    if (
        result.validation is not None
        and result.validation.reasons
    ):
        print(
            "Validation Reasons:"
        )

        for reason in (
            result.validation.reasons
        ):
            print(
                f"- {reason}"
            )

    proposal = result.proposal

    if proposal is None:
        return

    print(
        f"Action: "
        f"{proposal.action.value}"
    )

    print(
        f"Setup Quality: "
        f"{proposal.setup_quality.value}"
    )

    print(
        f"Confidence: "
        f"{proposal.confidence}"
    )

    print(
        f"Evidence Count: "
        f"{len(proposal.evidence)}"
    )

    print(
        f"Thesis: "
        f"{proposal.thesis}"
    )

    print(
        "Evidence:"
    )

    for item in proposal.evidence:
        print(
            f"- [{item.direction.value}] "
            f"{item.context_path} = "
            f"{item.value}"
        )


def print_summary(
    records: list[dict],
):
    total = len(records)

    accepted = sum(
        1
        for record in records
        if record["accepted"]
    )

    times = [
        record["elapsed"]
        for record in records
    ]

    categories = Counter(
        record["category"]
        for record in records
    )

    actions = Counter(
        record["action"]
        for record in records
        if record["action"] is not None
    )

    qualities = Counter(
        record["quality"]
        for record in records
        if record["quality"] is not None
    )

    confidences = [
        record["confidence"]
        for record in records
        if record["confidence"] is not None
    ]

    print(
        "\n"
        + "=" * 70
    )

    print(
        "GROQ BENCHMARK SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"Model: {GROQ_MODEL}"
    )

    print(
        f"Measured Runs: {total}"
    )

    print(
        f"Accepted: "
        f"{accepted}/{total}"
    )

    print(
        f"Acceptance Rate: "
        f"{accepted / total * 100:.1f}%"
    )

    print(
        f"Average Time: "
        f"{mean(times):.2f}s"
    )

    print(
        f"Median Time: "
        f"{median(times):.2f}s"
    )

    print(
        "\nResult Categories:"
    )

    for category, count in (
        categories.items()
    ):
        print(
            f"- {category}: {count}"
        )

    print(
        "\nActions:"
    )

    if actions:
        for action, count in actions.items():
            print(
                f"- {action}: {count}"
            )
    else:
        print(
            "- No valid actions"
        )

    print(
        "\nSetup Qualities:"
    )

    if qualities:
        for quality, count in (
            qualities.items()
        ):
            print(
                f"- {quality}: {count}"
            )
    else:
        print(
            "- No valid setup qualities"
        )

    if confidences:
        print(
            "\nConfidence:"
        )

        print(
            f"- Average: "
            f"{mean(confidences):.3f}"
        )

        print(
            f"- Min: "
            f"{min(confidences):.3f}"
        )

        print(
            f"- Max: "
            f"{max(confidences):.3f}"
        )


def main():
    print(
        "=== Sprint 3 — "
        "GroqCloud Reliability Benchmark ==="
    )

    validate_groq_settings()

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting live market data..."
        )

        sleep(5)

        # Build ONE fixed context so every
        # model call sees the same market.
        context = (
            MarketContextBuilder(
                runner=runner,
                orderbook_depth_levels=10,
            )
            .build(
                require_healthy=True
            )
        )

        print(
            "\n=== FIXED CONTEXT ==="
        )

        print(
            "Generated:",
            context.generated_at_utc.isoformat(),
        )

        print(
            "Alignment:",
            context.technical
            .trend_alignment.value,
        )

        print(
            "15m:",
            context.technical
            .timeframe_15m.trend.value,
        )

        print(
            "1h:",
            context.technical
            .timeframe_1h.trend.value,
        )

        print(
            "4h:",
            context.technical
            .timeframe_4h.trend.value,
        )

        print(
            f"\nModel: {GROQ_MODEL}"
        )

        service = build_service()

        for warmup in range(
            WARMUP_RUNS
        ):
            print(
                f"\nWarm-up "
                f"{warmup + 1}/"
                f"{WARMUP_RUNS}..."
            )

            result, elapsed = run_once(
                service,
                context,
            )

            print(
                f"Warm-up: "
                f"{elapsed:.2f}s "
                f"({classify_result(result)})"
            )

        records = []

        for run_number in range(
            1,
            MEASURED_RUNS + 1,
        ):
            print(
                f"\nMeasured run "
                f"{run_number}/"
                f"{MEASURED_RUNS}..."
            )

            result, elapsed = run_once(
                service,
                context,
            )

            proposal = result.proposal

            records.append(
                {
                    "elapsed": elapsed,
                    "accepted": (
                        result.accepted
                    ),
                    "category": (
                        classify_result(
                            result
                        )
                    ),
                    "action": (
                        proposal.action.value
                        if proposal is not None
                        else None
                    ),
                    "quality": (
                        proposal
                        .setup_quality.value
                        if proposal is not None
                        else None
                    ),
                    "confidence": (
                        proposal.confidence
                        if proposal is not None
                        else None
                    ),
                }
            )

            print_run(
                run_number,
                result,
                elapsed,
            )

            # Small pause to avoid unnecessary
            # burst pressure on free-tier limits.
            sleep(1)

        print_summary(
            records
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()