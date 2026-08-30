"""Measure API latency for Task 8.8 performance reporting."""

from __future__ import annotations

import asyncio
import statistics
import time
import uuid

from fastapi.testclient import TestClient

from app.main import app


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * pct))
    return ordered[index]


def measure_head_agent_phases(client: TestClient, company_id: str) -> dict[str, float]:
    """Single Head Agent request with phase timing via service instrumentation."""
    from unittest.mock import patch

    from app.services.head_agent import recommend_next_action

    phases: dict[str, float] = {}
    marks: dict[str, float] = {}

    def mark(name: str) -> None:
        marks[name] = time.perf_counter()

    async def timed_recommend(*args, **kwargs):
        mark("t0_request")
        # Patch context builder and provider inside recommend - use real path via API instead
        return await recommend_next_action(*args, **kwargs)

    # Use HTTP client for end-to-end measurement
    mark("start")
    response = client.post(
        f"/api/v1/companies/{company_id}/head-agent/recommend",
        json={"question": "What should we do next to get more customers?"},
    )
    mark("end")
    phases["e2e_total_ms"] = (marks["end"] - marks["start"]) * 1000
    phases["status_code"] = float(response.status_code)
    return phases


def run_benchmark() -> None:
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

    endpoints = {
        "objectives": f"/api/v1/companies/{company_id}/objectives",
        "approvals": f"/api/v1/companies/{company_id}/approvals",
        "tasks": f"/api/v1/companies/{company_id}/objective-tasks",
        "learnings": f"/api/v1/companies/{company_id}/learnings",
        "brain_context": f"/api/v1/companies/{company_id}/brain/context",
    }

    results: dict[str, list[float]] = {name: [] for name in endpoints}
    samples = 3

    for _ in range(samples):
        for name, path in endpoints.items():
            start = time.perf_counter()
            response = client.get(path)
            elapsed = (time.perf_counter() - start) * 1000
            results[name].append(elapsed)
            if response.status_code >= 400:
                print(f"WARN {name} returned {response.status_code}")

    print("=== List endpoint latency (ms) ===")
    for name, values in results.items():
        print(
            f"{name}: avg={statistics.mean(values):.1f} "
            f"p50={percentile(values, 0.5):.1f} p95={percentile(values, 0.95):.1f}"
        )

    head_samples: list[float] = []
    print("\n=== Head Agent recommend (live provider, e2e) ===")
    for i in range(2):
        start = time.perf_counter()
        response = client.post(
            f"/api/v1/companies/{company_id}/head-agent/recommend",
            json={"question": "What should we do next to get more customers?"},
        )
        elapsed = (time.perf_counter() - start) * 1000
        head_samples.append(elapsed)
        print(f"sample {i + 1}: {elapsed:.1f}ms status={response.status_code}")
        if response.status_code >= 400:
            print(response.text[:200])

    if head_samples:
        print(
            f"head_agent: avg={statistics.mean(head_samples):.1f} "
            f"p50={percentile(head_samples, 0.5):.1f} "
            f"p95={percentile(head_samples, 0.95):.1f}"
        )
        print("NOTE: Head Agent latency is dominated by LLM provider round-trip when live.")


if __name__ == "__main__":
    run_benchmark()
