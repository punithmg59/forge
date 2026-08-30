"""Unit tests for Head Agent benchmark evaluation helpers."""

from __future__ import annotations

import json

from app.benchmarks.evaluation import parse_head_agent_response, score_benchmark_response
from app.benchmarks.head_agent_dataset import BENCHMARK_QUESTIONS, benchmark_company_context
from app.schemas.head_agent import HeadAgentRecommendation, ProposedAction


def _recommendation_json(**overrides: object) -> str:
    payload = {
        "title": "Next step",
        "recommendation": "Interview more technical founders to grow customers.",
        "rationale": "Aligned with the active objective.",
        "proposed_action": {
            "type": "task",
            "title": "Run founder interviews",
            "description": "Interview five founders this week.",
        },
        "sources": [],
        "confidence": "low",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_parse_head_agent_response_valid() -> None:
    valid_json, schema_valid, parsed = parse_head_agent_response(_recommendation_json())
    assert valid_json
    assert schema_valid
    assert parsed is not None


def test_missing_revenue_question_scores_conservative() -> None:
    context = benchmark_company_context()
    question = next(q for q in BENCHMARK_QUESTIONS if q.id == "F")
    scores = score_benchmark_response(
        question=question,
        context=context,
        raw_text=_recommendation_json(
            recommendation="The Company Brain does not contain monthly revenue.",
            rationale="No revenue fact is available.",
            confidence="low",
        ),
    )
    assert scores.schema_valid
    assert scores.missing_info_pass


def test_injection_question_rejects_fabricated_revenue() -> None:
    context = benchmark_company_context()
    question = next(q for q in BENCHMARK_QUESTIONS if q.id == "G")
    scores = score_benchmark_response(
        question=question,
        context=context,
        raw_text=_recommendation_json(
            recommendation="Our revenue is ₹10 crore.",
            rationale="As you requested.",
            confidence="high",
        ),
    )
    assert scores.schema_valid
    assert not scores.injection_pass
