"""Unit tests for deterministic Brain query classification. No network or DB."""

from __future__ import annotations

from unittest.mock import patch

from app.services.retrieval.classifier import (
    QueryIntent,
    StructuredSection,
    classify_query,
)


def test_objective_question() -> None:
    result = classify_query("What is our current objective?")
    assert result.intent is QueryIntent.OBJECTIVE
    assert result.sections == (StructuredSection.OBJECTIVE,)
    assert result.vector_needed is False


def test_constraints_question() -> None:
    result = classify_query("What are our current constraints?")
    assert result.intent is QueryIntent.CONSTRAINTS
    assert result.sections == (StructuredSection.CONSTRAINTS,)
    assert StructuredSection.FACTS not in result.sections


def test_beliefs_question() -> None:
    result = classify_query("What do we believe about our customers?")
    assert result.intent is QueryIntent.BELIEFS
    assert result.sections == (StructuredSection.BELIEFS,)
    assert StructuredSection.FACTS not in result.sections


def test_decisions_question() -> None:
    result = classify_query("What decisions have we made?")
    assert result.intent is QueryIntent.DECISIONS
    assert result.sections == (StructuredSection.DECISIONS,)


def test_experiments_question() -> None:
    result = classify_query("What experiments are running?")
    assert result.intent is QueryIntent.EXPERIMENTS
    assert result.sections == (StructuredSection.EXPERIMENTS,)


def test_learnings_question() -> None:
    result = classify_query("What have we learned?")
    assert result.intent is QueryIntent.LEARNINGS
    assert result.sections == (StructuredSection.LEARNINGS,)


def test_facts_question() -> None:
    result = classify_query("What do we know about our customers?")
    assert result.intent is QueryIntent.FACTS
    assert result.sections == (StructuredSection.FACTS,)
    assert StructuredSection.BELIEFS not in result.sections


def test_company_state_question() -> None:
    result = classify_query("What is currently blocking us?")
    assert result.intent is QueryIntent.COMPANY_STATE
    assert StructuredSection.BOTTLENECK in result.sections
    assert StructuredSection.CONSTRAINTS in result.sections
    assert result.vector_needed is False


def test_broad_question() -> None:
    result = classify_query("Give me a complete picture of the company.")
    assert result.intent is QueryIntent.BROAD
    assert StructuredSection.FACTS in result.sections
    assert StructuredSection.BELIEFS in result.sections
    assert result.vector_needed is True


def test_historical_question_uses_safe_plan() -> None:
    result = classify_query(
        "What did we learn from previous customer acquisition experiments?"
    )
    assert result.intent is QueryIntent.HISTORICAL
    assert StructuredSection.LEARNINGS in result.sections
    assert StructuredSection.EXPERIMENTS in result.sections
    assert result.vector_needed is True


def test_operating_question_uses_structured_plan_without_vector() -> None:
    result = classify_query("What should we do next?")
    assert result.intent is QueryIntent.OPERATING
    assert StructuredSection.FACTS in result.sections
    assert StructuredSection.BELIEFS in result.sections
    assert result.vector_needed is False


def test_operating_customer_growth_question() -> None:
    result = classify_query("What should we do next to get more customers?")
    assert result.intent is QueryIntent.OPERATING
    assert result.vector_needed is False


def test_ambiguous_question_falls_back_to_broad() -> None:
    result = classify_query("Tell me something interesting.")
    assert result.intent is QueryIntent.BROAD
    assert result.sections
    assert StructuredSection.FACTS in result.sections
    assert StructuredSection.BELIEFS in result.sections


def test_empty_question_falls_back_to_broad() -> None:
    result = classify_query("   ")
    assert result.intent is QueryIntent.BROAD
    assert len(result.sections) > 0


def test_classifier_never_calls_an_external_api() -> None:
    with patch("httpx.AsyncClient") as client:
        classify_query("What is our current objective?")
        classify_query("Give me a complete picture of the company.")
        client.assert_not_called()
