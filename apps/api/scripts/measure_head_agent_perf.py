"""Measure Head Agent phase latency for Task 8.9 performance reporting."""

from __future__ import annotations

import logging
import statistics
import time
import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.brain import CompanyContext
from app.services.head_agent_prompt import estimate_head_agent_prompt_chars
from app.services.retrieval.classifier import classify_query

QUESTION = "What should we do next to get more customers?"
SAMPLES = 5


@dataclass
class HeadAgentPerfSample:
    retrieval_ms: float
    prompt_build_ms: float
    llm_ms: float
    parsing_ms: float
    persistence_ms: float
    total_ms: float
    prompt_chars: int
    output_chars: int
    vector_used: bool


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * pct))
    return ordered[index]


class PerfLogHandler(logging.Handler):
    """Capture head_agent_perf log lines for phase breakdown."""

    def __init__(self) -> None:
        super().__init__()
        self.samples: list[HeadAgentPerfSample] = []

    def emit(self, record: logging.LogRecord) -> None:
        if not record.getMessage().startswith("head_agent_perf"):
            return
        args = record.args
        if not isinstance(args, tuple) or len(args) < 10:
            return
        self.samples.append(
            HeadAgentPerfSample(
                retrieval_ms=float(args[1]),
                prompt_build_ms=float(args[2]),
                llm_ms=float(args[3]),
                parsing_ms=float(args[4]),
                persistence_ms=float(args[5]),
                total_ms=float(args[6]),
                prompt_chars=int(args[7]),
                output_chars=int(args[8]),
                vector_used=bool(args[9]),
            )
        )


def run_benchmark() -> None:
    classification = classify_query(QUESTION)
    print(
        f"Query classification: {classification.intent.value} "
        f"vector_needed={classification.vector_needed}"
    )

    client = TestClient(app)
    email = f"bench-{uuid.uuid4()}@example.com"
    register = client.post(
        "/api/v1/auth/register",
        json={"name": "Bench", "email": email, "password": "valid-pass-1"},
    )
    if register.status_code != 201:
        print(f"Register failed: {register.status_code} {register.text}")
        return

    company = client.post(
        "/api/v1/companies",
        json={
            "name": "Bench Co",
            "description": "benchmark",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    company_id = company.json()["id"]

    client.post(
        f"/api/v1/companies/{company_id}/objectives",
        json={
            "title": "Grow customers",
            "description": "Get more paying customers this quarter",
            "priority": 1,
            "status": "active",
        },
    )

    handler = PerfLogHandler()
    service_logger = logging.getLogger("app.services.head_agent")
    service_logger.addHandler(handler)
    service_logger.setLevel(logging.INFO)

    totals: list[float] = []
    failures = 0

    print(f"\n=== Head Agent recommend ({SAMPLES} live samples) ===")
    for i in range(SAMPLES):
        start = time.perf_counter()
        response = client.post(
            f"/api/v1/companies/{company_id}/head-agent/recommend",
            json={"question": QUESTION},
        )
        e2e_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        print(f"sample {i + 1}: e2e={e2e_ms:.1f}ms status={status}")
        if status >= 400:
            failures += 1
            print(response.text[:300])
            continue
        totals.append(e2e_ms)
        if handler.samples:
            sample = handler.samples[-1]
            print(
                f"  phases_ms retrieval={sample.retrieval_ms:.1f} "
                f"prompt={sample.prompt_build_ms:.1f} llm={sample.llm_ms:.1f} "
                f"parsing={sample.parsing_ms:.1f} persist={sample.persistence_ms:.1f} "
                f"prompt_chars={sample.prompt_chars} output_chars={sample.output_chars} "
                f"vector={sample.vector_used}"
            )

    service_logger.removeHandler(handler)

    successful = handler.samples
    if totals:
        print("\n=== Summary (successful samples) ===")
        print(
            f"total e2e: avg={statistics.mean(totals):.1f} "
            f"p50={percentile(totals, 0.5):.1f} p95={percentile(totals, 0.95):.1f}"
        )
    if successful:
        retrieval = [s.retrieval_ms for s in successful]
        prompt_build = [s.prompt_build_ms for s in successful]
        llm = [s.llm_ms for s in successful]
        parsing = [s.parsing_ms for s in successful]
        persistence = [s.persistence_ms for s in successful]
        prompt_chars = [s.prompt_chars for s in successful]
        output_chars = [s.output_chars for s in successful]
        print(
            f"retrieval_ms: avg={statistics.mean(retrieval):.1f} "
            f"p50={percentile(retrieval, 0.5):.1f}"
        )
        print(
            f"prompt_build_ms: avg={statistics.mean(prompt_build):.1f} "
            f"p50={percentile(prompt_build, 0.5):.1f}"
        )
        print(
            f"llm_ms: avg={statistics.mean(llm):.1f} "
            f"p50={percentile(llm, 0.5):.1f} p95={percentile(llm, 0.95):.1f}"
        )
        print(
            f"parsing_ms: avg={statistics.mean(parsing):.1f} "
            f"p50={percentile(parsing, 0.5):.1f}"
        )
        print(
            f"persistence_ms: avg={statistics.mean(persistence):.1f} "
            f"p50={percentile(persistence, 0.5):.1f}"
        )
        print(
            f"prompt_chars: avg={statistics.mean(prompt_chars):.0f} "
            f"output_chars: avg={statistics.mean(output_chars):.0f}"
        )
    print(f"failures: {failures}/{SAMPLES}")

    empty_chars = estimate_head_agent_prompt_chars(question=QUESTION, context=CompanyContext())
    print(f"\nEmpty-context prompt_chars (reference): {empty_chars}")


if __name__ == "__main__":
    run_benchmark()
