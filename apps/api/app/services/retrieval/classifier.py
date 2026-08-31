"""Deterministic question classification. No LLM and no retrieval."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class QueryIntent(str, Enum):
    OBJECTIVE = "OBJECTIVE"
    CONSTRAINTS = "CONSTRAINTS"
    BELIEFS = "BELIEFS"
    DECISIONS = "DECISIONS"
    EXPERIMENTS = "EXPERIMENTS"
    LEARNINGS = "LEARNINGS"
    FACTS = "FACTS"
    COMPANY_STATE = "COMPANY_STATE"
    OPERATING = "OPERATING"
    HISTORICAL = "HISTORICAL"
    BROAD = "BROAD"


class StructuredSection(str, Enum):
    COMPANY = "company"
    OBJECTIVE = "objective"
    BOTTLENECK = "bottleneck"
    CONSTRAINTS = "constraints"
    FACTS = "facts"
    BELIEFS = "beliefs"
    DECISIONS = "decisions"
    EXPERIMENTS = "experiments"
    LEARNINGS = "learnings"


ALL_STRUCTURED_SECTIONS: tuple[StructuredSection, ...] = (
    StructuredSection.COMPANY,
    StructuredSection.OBJECTIVE,
    StructuredSection.BOTTLENECK,
    StructuredSection.CONSTRAINTS,
    StructuredSection.FACTS,
    StructuredSection.BELIEFS,
    StructuredSection.DECISIONS,
    StructuredSection.EXPERIMENTS,
    StructuredSection.LEARNINGS,
)

SECTIONS_FOR_INTENT: dict[QueryIntent, tuple[StructuredSection, ...]] = {
    QueryIntent.OBJECTIVE: (StructuredSection.OBJECTIVE,),
    QueryIntent.CONSTRAINTS: (StructuredSection.CONSTRAINTS,),
    QueryIntent.BELIEFS: (StructuredSection.BELIEFS,),
    QueryIntent.FACTS: (StructuredSection.FACTS,),
    QueryIntent.DECISIONS: (StructuredSection.DECISIONS,),
    QueryIntent.EXPERIMENTS: (StructuredSection.EXPERIMENTS,),
    QueryIntent.LEARNINGS: (StructuredSection.LEARNINGS,),
    QueryIntent.COMPANY_STATE: (
        StructuredSection.COMPANY,
        StructuredSection.OBJECTIVE,
        StructuredSection.BOTTLENECK,
        StructuredSection.CONSTRAINTS,
    ),
    QueryIntent.OPERATING: ALL_STRUCTURED_SECTIONS,
    QueryIntent.HISTORICAL: (
        StructuredSection.LEARNINGS,
        StructuredSection.EXPERIMENTS,
        StructuredSection.DECISIONS,
    ),
    QueryIntent.BROAD: ALL_STRUCTURED_SECTIONS,
}

_INTENT_TERMS: dict[QueryIntent, tuple[str, ...]] = {
    QueryIntent.OBJECTIVE: (
        "current objective",
        "our objective",
        "objectives",
        "objective",
        "our goal",
        "current goal",
        "goals",
        "goal",
    ),
    QueryIntent.CONSTRAINTS: (
        "current constraints",
        "our constraints",
        "constraints",
        "constraint",
        "limitations",
        "limitation",
        "budget",
    ),
    QueryIntent.BELIEFS: (
        "do we believe",
        "we believe",
        "beliefs",
        "belief",
        "believe",
        "we think",
        "assumptions",
        "assumption",
    ),
    QueryIntent.DECISIONS: (
        "decisions have we made",
        "decisions",
        "decision",
        "have we decided",
        "we decided",
        "decided",
    ),
    QueryIntent.EXPERIMENTS: (
        "experiments are running",
        "experiments",
        "experiment",
        "a/b test",
        "ab test",
    ),
    QueryIntent.LEARNINGS: (
        "have we learned",
        "what have we learned",
        "learnings",
        "learned",
        "what did we learn",
    ),
    QueryIntent.FACTS: (
        "what do we know",
        "do we know",
        "know about",
        "facts",
        "fact",
        "confirmed",
    ),
    QueryIntent.COMPANY_STATE: (
        "currently blocking",
        "blocking us",
        "blocked",
        "blocking",
        "bottlenecks",
        "bottleneck",
        "in the way",
    ),
    QueryIntent.OPERATING: (
        "what should",
        "should we do",
        "should we",
        "do next",
        "focus on next",
        "focus on",
        "next step",
        "get more",
        "grow",
        "growth",
        "customers",
        "acquire",
        "highest-leverage",
        "recommend",
    ),
    QueryIntent.BROAD: (
        "complete picture",
        "full picture",
        "entire company",
        "whole company",
        "overview",
        "everything about",
    ),
    QueryIntent.HISTORICAL: (
        "previous",
        "previously",
        "in the past",
        "historically",
        "past experiments",
        "prior",
    ),
}

_VECTOR_INTENTS = frozenset({QueryIntent.HISTORICAL, QueryIntent.BROAD})
_SCORED_INTENTS = tuple(
    intent for intent in QueryIntent if intent is not QueryIntent.BROAD
)


class QueryClassification(BaseModel):
    """Retrieval plan only. The classifier does not fetch Brain data."""

    model_config = ConfigDict(extra="forbid")

    intent: QueryIntent
    sections: tuple[StructuredSection, ...]
    vector_needed: bool
    matched_terms: tuple[str, ...] = Field(default_factory=tuple)


def classify_query(question: str) -> QueryClassification:
    """Map a question to later retrieval work using keyword rules only."""
    text = " ".join(question.lower().split())
    scores: dict[QueryIntent, list[str]] = {intent: [] for intent in QueryIntent}

    for intent, terms in _INTENT_TERMS.items():
        for term in terms:
            if term in text:
                scores[intent].append(term)

    historical_hits = scores[QueryIntent.HISTORICAL]
    past_topic = scores[QueryIntent.LEARNINGS] or scores[QueryIntent.EXPERIMENTS]
    if historical_hits and past_topic:
        return _result(QueryIntent.HISTORICAL, tuple(historical_hits + past_topic))

    ranked = sorted(
        (
            (intent, matches)
            for intent, matches in scores.items()
            if intent in _SCORED_INTENTS and matches
        ),
        key=lambda item: (-_best_term_length(item[1]), item[0].value),
    )
    if not ranked:
        return _result(QueryIntent.BROAD, tuple(scores[QueryIntent.BROAD]))

    top_intent, top_matches = ranked[0]
    top_len = _best_term_length(top_matches)
    tied = [
        intent
        for intent, matches in ranked
        if _best_term_length(matches) == top_len
    ]
    if len(tied) > 1:
        return _result(QueryIntent.BROAD, tuple(top_matches))
    return _result(top_intent, tuple(top_matches))


def _best_term_length(matches: list[str]) -> int:
    return max(len(term) for term in matches)


def _result(intent: QueryIntent, matched_terms: tuple[str, ...]) -> QueryClassification:
    return QueryClassification(
        intent=intent,
        sections=SECTIONS_FOR_INTENT[intent],
        vector_needed=intent in _VECTOR_INTENTS,
        matched_terms=matched_terms,
    )
