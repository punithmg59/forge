"""Live Head Agent LLM model benchmark for Task 8.10."""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field

from app.benchmarks.evaluation import score_benchmark_response
from app.benchmarks.head_agent_dataset import (
    BENCHMARK_QUESTIONS,
    LATENCY_QUESTION_ID,
    NEWTRON_BENCHMARK_MODELS,
    benchmark_company_context,
)
from app.core.config import Settings
from app.services.head_agent_prompt import (
    build_head_agent_completion_request,
    estimate_head_agent_prompt_chars,
)
from app.services.llm.errors import ProviderError
from app.services.llm.newtron import NewtronProvider


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * pct))
    return ordered[index]


LATENCY_SAMPLES = 5


@dataclass
class ModelBenchmarkResult:
    model: str
    latency_ms: list[float] = field(default_factory=list)
    latency_failures: int = 0
    json_valid: int = 0
    schema_valid: int = 0
    question_total: int = 0
    provider_failures: int = 0
    timeouts: int = 0
    quality_total: int = 0
    grounding_pass: int = 0
    grounding_checks: int = 0
    injection_pass: int = 0
    missing_info_pass: int = 0
    prompt_chars: list[int] = field(default_factory=list)
    output_chars: list[int] = field(default_factory=list)
    usable: bool = True
    notes: str = ""


async def run_model_benchmark(model: str, settings: Settings) -> ModelBenchmarkResult:
    result = ModelBenchmarkResult(model=model)
    provider = NewtronProvider.from_settings(settings.model_copy(update={"llm_model": model}))
    context = benchmark_company_context()

    latency_question = next(q for q in BENCHMARK_QUESTIONS if q.id == LATENCY_QUESTION_ID)

    for _ in range(LATENCY_SAMPLES):
        request = build_head_agent_completion_request(
            question=latency_question.question,
            context=context,
        )
        request = request.model_copy(update={"model": model})
        start = time.perf_counter()
        try:
            await provider.complete(request)
            result.latency_ms.append((time.perf_counter() - start) * 1000)
        except ProviderError as exc:
            result.latency_failures += 1
            if "timed out" in str(exc).lower():
                result.timeouts += 1
            else:
                result.provider_failures += 1
            if result.latency_failures >= 2 and not result.latency_ms:
                result.usable = False
                result.notes = f"latency_probe_failed: {exc}"
                await provider.aclose()
                return result

    for item in BENCHMARK_QUESTIONS:
        result.question_total += 1
        request = build_head_agent_completion_request(question=item.question, context=context)
        request = request.model_copy(update={"model": model})
        result.prompt_chars.append(
            estimate_head_agent_prompt_chars(question=item.question, context=context)
        )
        try:
            completion = await provider.complete(request)
        except ProviderError as exc:
            result.provider_failures += 1
            if "timed out" in str(exc).lower():
                result.timeouts += 1
            continue

        result.output_chars.append(len(completion.text))
        scores = score_benchmark_response(
            question=item,
            context=context,
            raw_text=completion.text,
        )
        if scores.valid_json:
            result.json_valid += 1
        if scores.schema_valid:
            result.schema_valid += 1
            result.quality_total += scores.total_quality
        if item.id == "G":
            result.grounding_checks += 1
            if scores.injection_pass:
                result.injection_pass += 1
                result.grounding_pass += 1
        if item.id == "F":
            result.grounding_checks += 1
            if scores.missing_info_pass:
                result.missing_info_pass += 1
                result.grounding_pass += 1

    await provider.aclose()
    if result.schema_valid < max(6, result.question_total - 2):
        result.usable = False
        if not result.notes:
            result.notes = "schema_valid_rate_too_low"
    return result


def summarize(result: ModelBenchmarkResult) -> dict[str, object]:
    lat = result.latency_ms
    return {
        "model": result.model,
        "usable": result.usable,
        "notes": result.notes,
        "latency_avg_ms": round(statistics.mean(lat), 1) if lat else None,
        "latency_p50_ms": round(percentile(lat, 0.5), 1) if lat else None,
        "latency_p95_ms": round(percentile(lat, 0.95), 1) if lat else None,
        "latency_samples": len(lat),
        "json_valid": f"{result.json_valid}/{result.question_total}",
        "schema_valid": f"{result.schema_valid}/{result.question_total}",
        "quality_avg_out_of_10": (
            round(result.quality_total / result.schema_valid, 1)
            if result.schema_valid
            else None
        ),
        "grounding_pass": f"{result.grounding_pass}/{result.grounding_checks}",
        "provider_failures": result.provider_failures,
        "timeouts": result.timeouts,
        "prompt_chars_avg": (
            round(statistics.mean(result.prompt_chars), 0) if result.prompt_chars else None
        ),
        "output_chars_avg": (
            round(statistics.mean(result.output_chars), 0) if result.output_chars else None
        ),
    }


async def main() -> None:
    settings = Settings()
    if not settings.newtron_api_key.strip():
        print("NEWTRON_API_KEY not configured — cannot run live benchmark")
        return

    print(f"provider=newtron models={list(NEWTRON_BENCHMARK_MODELS)}")
    summaries: list[dict[str, object]] = []
    for model in NEWTRON_BENCHMARK_MODELS:
        print(f"\n--- {model} ---")
        result = await run_model_benchmark(model, settings)
        summary = summarize(result)
        summaries.append(summary)
        print(json.dumps(summary, indent=2))

    print("\n=== SUMMARY JSON ===")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
