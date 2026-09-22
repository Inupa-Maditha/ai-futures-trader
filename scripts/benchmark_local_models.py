from __future__ import annotations

from collections import Counter
from statistics import mean, median
from time import perf_counter, sleep

from config.settings import (
    LM_STUDIO_BASE_URL,
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

from decision_engine.providers.lmstudio_provider import (
    LMStudioProvider,
)

from decision_engine.validator import (
    DecisionValidator,
)

from market_data.runner import (
    MarketDataRunner,
)


MODELS = [
    "qwen2.5-3b-instruct",
    "google/gemma-3-4b",
]

WARMUP_RUNS = 1
MEASURED_RUNS = 3

# Benchmark only.
# Production default remains 120 seconds.
BENCHMARK_CONTEXT_MAX_AGE_SECONDS = 900


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


def build_service(
    model: str,
) -> LLMDecisionService:

    provider = LMStudioProvider(
        base_url=LM_STUDIO_BASE_URL,
        model=model,
    )

    # Longer freshness window ONLY for
    # repeated same-context benchmarking.
    validator = DecisionValidator(
        max_context_age_seconds=(
            BENCHMARK_CONTEXT_MAX_AGE_SECONDS
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
        f"\nRun {run_number}"
    )

    print(
        f"Time: {elapsed:.2f}s"
    )

    print(
        f"Result: {category}"
    )

    if result.proposal is not None:
        print(
            "Action:",
            result.proposal.action.value,
        )

        print(
            "Setup Quality:",
            result.proposal
            .setup_quality.value,
        )

        print(
            "Confidence:",
            result.proposal.confidence,
        )

        print(
            "Evidence Count:",
            len(
                result.proposal.evidence
            ),
        )

    if result.error:
        print(
            "Error:",
            result.error,
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


def print_summary(
    model: str,
    records: list[dict],
):
    times = [
        record["elapsed"]
        for record in records
    ]

    accepted = sum(
        1
        for record in records
        if record["accepted"]
    )

    categories = Counter(
        record["category"]
        for record in records
    )

    actions = Counter(
        record["action"]
        for record in records
        if record["action"]
        is not None
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        f"SUMMARY: {model}"
    )

    print(
        "=" * 70
    )

    print(
        f"Measured Runs: "
        f"{len(records)}"
    )

    print(
        f"Accepted: "
        f"{accepted}/"
        f"{len(records)}"
    )

    print(
        f"Acceptance Rate: "
        f"{accepted / len(records) * 100:.1f}%"
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

    if not actions:
        print(
            "- No valid actions"
        )

    else:
        for action, count in (
            actions.items()
        ):
            print(
                f"- {action}: {count}"
            )


def main():
    print(
        "=== Sprint 3 — "
        "Local LLM Reliability Benchmark ==="
    )

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting live market data..."
        )

        sleep(5)

        # IMPORTANT:
        # Build the market context exactly once.
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
            "\n=== FIXED BENCHMARK CONTEXT ==="
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

        all_results = {}

        for model in MODELS:
            print(
                "\n"
                + "#" * 70
            )

            print(
                f"MODEL: {model}"
            )

            print(
                "#" * 70
            )

            service = build_service(
                model
            )

            # Warm-up is not included
            # in benchmark statistics.
            for warmup in range(
                WARMUP_RUNS
            ):
                print(
                    f"\nWarm-up "
                    f"{warmup + 1}/"
                    f"{WARMUP_RUNS}..."
                )

                warmup_result, warmup_time = (
                    run_once(
                        service,
                        context,
                    )
                )

                print(
                    f"Warm-up complete: "
                    f"{warmup_time:.2f}s "
                    f"({classify_result(warmup_result)})"
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

                category = (
                    classify_result(
                        result
                    )
                )

                action = None

                if result.proposal is not None:
                    action = (
                        result.proposal
                        .action.value
                    )

                records.append(
                    {
                        "elapsed": elapsed,
                        "accepted": (
                            result.accepted
                        ),
                        "category": category,
                        "action": action,
                    }
                )

                print_run(
                    run_number,
                    result,
                    elapsed,
                )

            all_results[model] = (
                records
            )

            print_summary(
                model,
                records,
            )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "BENCHMARK COMPLETE"
        )

        print(
            "=" * 70
        )

        for model, records in (
            all_results.items()
        ):
            accepted = sum(
                record["accepted"]
                for record in records
            )

            avg_time = mean(
                record["elapsed"]
                for record in records
            )

            print(
                f"{model}: "
                f"{accepted}/"
                f"{len(records)} accepted, "
                f"avg {avg_time:.2f}s"
            )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()