"""Deterministic specialist routing. No LLM and no Brain retrieval."""

from __future__ import annotations

from app.schemas.specialized_agent_types import DOMAIN_TO_AGENT_TYPE, AgentDomain
from app.schemas.specialized_routing import (
    DeterministicRoutingResult,
    DeterministicRoutingStatus,
    RoutingConfidence,
    RoutingMethod,
    SpecializedRoutingDecision,
)
from app.schemas.specialized_routing_types import INTENT_TO_DOMAIN, RoutingIntent
from app.services.specialized_agents.routing.intents import (
    AMBIGUOUS_OPERATING_PATTERNS,
    INJECTION_PATTERNS,
    INTENT_TERMS,
)

STRONG_MATCH_MIN_TERM_LENGTH = 10
STRONG_MATCH_MIN_HITS = 2


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _best_term_length(matches: list[str]) -> int:
    return max(len(term) for term in matches)


def _is_ambiguous_operating(text: str) -> bool:
    return any(pattern in text for pattern in AMBIGUOUS_OPERATING_PATTERNS)


def _has_injection_pattern(text: str) -> bool:
    return any(pattern in text for pattern in INJECTION_PATTERNS)


def _score_intents(text: str) -> dict[RoutingIntent, list[str]]:
    scores: dict[RoutingIntent, list[str]] = {
        intent: [] for intent in INTENT_TERMS
    }
    for intent, terms in INTENT_TERMS.items():
        for term in terms:
            if term in text:
                scores[intent].append(term)
    return scores


def _domain_scores(scores: dict[RoutingIntent, list[str]]) -> dict[AgentDomain, list[str]]:
    by_domain: dict[AgentDomain, list[str]] = {
        AgentDomain.CUSTOMER_GROWTH: [],
        AgentDomain.PRODUCT: [],
    }
    for intent, matches in scores.items():
        if not matches:
            continue
        domain = INTENT_TO_DOMAIN[intent]
        if domain is not None:
            by_domain[domain].extend(matches)
    return by_domain


def _is_strong_domain_match(matches: list[str]) -> bool:
    if not matches:
        return False
    if len(matches) >= STRONG_MATCH_MIN_HITS:
        return True
    return _best_term_length(matches) >= STRONG_MATCH_MIN_TERM_LENGTH


def _pick_top_intent(
    scores: dict[RoutingIntent, list[str]],
    domain: AgentDomain,
) -> tuple[RoutingIntent, tuple[str, ...]]:
    domain_intents = [
        (intent, matches)
        for intent, matches in scores.items()
        if matches and INTENT_TO_DOMAIN[intent] == domain
    ]
    ranked = sorted(
        domain_intents,
        key=lambda item: (-_best_term_length(item[1]), -len(item[1]), item[0].value),
    )
    intent, matches = ranked[0]
    return intent, tuple(matches)


def head_agent_fallback_decision(
    *,
    reason: str,
    routing_method: RoutingMethod = "fallback",
    confidence: RoutingConfidence = "low",
) -> SpecializedRoutingDecision:
    return SpecializedRoutingDecision(
        selected_agent=None,
        domain=None,
        intent=RoutingIntent.GENERAL,
        confidence=confidence,
        reason=reason,
        fallback_to_head_agent=True,
        routing_method=routing_method,
        matched_terms=(),
    )


def classify_deterministic(question: str) -> DeterministicRoutingResult:
    """Map a founder question to a specialist using keyword rules only."""
    text = _normalize(question)

    if _has_injection_pattern(text):
        return DeterministicRoutingResult(status=DeterministicRoutingStatus.WEAK_MATCH)

    if _is_ambiguous_operating(text):
        domain_scores = _domain_scores(_score_intents(text))
        customer_hits = domain_scores[AgentDomain.CUSTOMER_GROWTH]
        product_hits = domain_scores[AgentDomain.PRODUCT]
        if not _is_strong_domain_match(customer_hits) and not _is_strong_domain_match(
            product_hits
        ):
            return DeterministicRoutingResult(
                status=DeterministicRoutingStatus.AMBIGUOUS,
                decision=head_agent_fallback_decision(
                    reason=(
                        "Question is an ambiguous operating question without a clear "
                        "customer/growth or product signal. Delegate to Head Agent."
                    ),
                    routing_method="fallback",
                ),
            )

    scores = _score_intents(text)
    domain_scores = _domain_scores(scores)

    customer_hits = domain_scores[AgentDomain.CUSTOMER_GROWTH]
    product_hits = domain_scores[AgentDomain.PRODUCT]
    customer_strong = _is_strong_domain_match(customer_hits)
    product_strong = _is_strong_domain_match(product_hits)

    if customer_strong and not product_strong:
        intent, matched = _pick_top_intent(scores, AgentDomain.CUSTOMER_GROWTH)
        selected = DOMAIN_TO_AGENT_TYPE[AgentDomain.CUSTOMER_GROWTH]
        return DeterministicRoutingResult(
            status=DeterministicRoutingStatus.STRONG_MATCH,
            decision=SpecializedRoutingDecision(
                selected_agent=selected,
                domain=AgentDomain.CUSTOMER_GROWTH,
                intent=intent,
                confidence="high",
                reason=(
                    f"Deterministic match for {intent.value} "
                    f"({', '.join(matched[:3])})."
                ),
                fallback_to_head_agent=False,
                routing_method="deterministic",
                matched_terms=matched,
            ),
        )

    if product_strong and not customer_strong:
        intent, matched = _pick_top_intent(scores, AgentDomain.PRODUCT)
        selected = DOMAIN_TO_AGENT_TYPE[AgentDomain.PRODUCT]
        return DeterministicRoutingResult(
            status=DeterministicRoutingStatus.STRONG_MATCH,
            decision=SpecializedRoutingDecision(
                selected_agent=selected,
                domain=AgentDomain.PRODUCT,
                intent=intent,
                confidence="high",
                reason=(
                    f"Deterministic match for {intent.value} "
                    f"({', '.join(matched[:3])})."
                ),
                fallback_to_head_agent=False,
                routing_method="deterministic",
                matched_terms=matched,
            ),
        )

    if customer_strong and product_strong:
        return DeterministicRoutingResult(status=DeterministicRoutingStatus.WEAK_MATCH)

    if customer_hits or product_hits:
        return DeterministicRoutingResult(status=DeterministicRoutingStatus.WEAK_MATCH)

    return DeterministicRoutingResult(status=DeterministicRoutingStatus.NO_MATCH)


def detect_mixed_domain_strong_match(question: str) -> bool:
    """True when both customer/growth and product have strong deterministic signals."""
    text = _normalize(question)
    scores = _score_intents(text)
    domain_scores = _domain_scores(scores)
    return (
        _is_strong_domain_match(domain_scores[AgentDomain.CUSTOMER_GROWTH])
        and _is_strong_domain_match(domain_scores[AgentDomain.PRODUCT])
    )
