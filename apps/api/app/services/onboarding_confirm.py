"""Atomic, idempotent Company Brain initialization from an onboarding draft."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utcnow
from app.models.company import Company
from app.models.company_belief import CompanyBelief
from app.models.company_brain_profile import CompanyBrainProfile
from app.models.company_constraint import CompanyConstraint
from app.models.company_fact import CompanyFact
from app.models.decision import Decision
from app.models.objective import Objective
from app.models.onboarding_draft import STATUS_CONFIRMED, OnboardingDraft
from app.models.user import User
from app.schemas.onboarding import MAX_ONBOARDING_STEP
from app.schemas.onboarding_confirm import ALLOWED_CONSTRAINT_TYPES, ALLOWED_STAGES, as_text

SOURCE_FOUNDER_INPUT = "founder_input"
ONBOARDING_DECISION_TITLE = "Initial Company Brain confirmed"
BELIEF_MARKERS = ("we believe", "we think", "i believe", "i think")


class ConfirmError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def onboarding_source_reference(company_id: uuid.UUID) -> str:
    return f"onboarding:{company_id}"


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _looks_like_belief(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in BELIEF_MARKERS)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _validate_and_extract(payload: dict[str, Any], current_step: int) -> dict[str, Any]:
    if current_step < MAX_ONBOARDING_STEP:
        raise ConfirmError(
            400,
            "Onboarding must be on the review step before confirmation",
        )

    company = _section(payload, "company")
    customer = _section(payload, "customer")
    situation = _section(payload, "current_situation")
    context = _section(payload, "context")

    name = as_text(company.get("name"))
    product_description = as_text(
        company.get("product_description") or company.get("description")
    )
    stage = as_text(company.get("stage"))
    target_customer = as_text(customer.get("target_customer"))
    objective_title = as_text(situation.get("objective") or situation.get("current_objective"))

    if not name:
        raise ConfirmError(400, "Company name is required")
    if not product_description:
        raise ConfirmError(400, "Product description is required")
    if not stage:
        raise ConfirmError(400, "Stage is required")
    if stage.lower() not in ALLOWED_STAGES:
        raise ConfirmError(400, "Stage must be one of: idea, mvp, growth, scale")
    if not target_customer:
        raise ConfirmError(400, "Target customer is required")
    if not objective_title:
        raise ConfirmError(400, "Current objective is required")

    return {
        "name": name,
        "product_description": product_description,
        "stage": stage.lower(),
        "target_customer": target_customer,
        "mission": as_text(context.get("mission") or company.get("mission")),
        "strategy": as_text(context.get("strategy")),
        "non_goals": as_text(context.get("non_goals")),
        "working_style": as_text(context.get("working_style")),
        "current_priorities": as_text(
            situation.get("priorities") or context.get("current_priorities")
        ),
        "bottleneck": as_text(situation.get("bottleneck") or situation.get("current_bottleneck")),
        "objective_title": objective_title,
        "objective_description": as_text(situation.get("objective_description")),
        "deadline": as_text(situation.get("deadline") or situation.get("urgency")),
        "beliefs": _collect_beliefs(customer, situation, context),
        "facts": _collect_facts(company, customer, situation, context),
        "constraints": _collect_constraints(situation, context),
    }


def _collect_beliefs(
    customer: dict[str, Any],
    situation: dict[str, Any],
    context: dict[str, Any],
) -> list[dict[str, str]]:
    collected: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(statement: str | None, reasoning: str | None = None) -> None:
        if not statement or statement in seen:
            return
        seen.add(statement)
        item: dict[str, str] = {"statement": statement}
        if reasoning:
            item["reasoning"] = reasoning
        collected.append(item)

    for key in ("problem", "problem_being_solved"):
        add(as_text(customer.get(key)))

    for raw in (
        *_as_list(customer.get("beliefs")),
        *_as_list(situation.get("beliefs")),
        *_as_list(context.get("beliefs")),
        situation.get("belief"),
        context.get("belief"),
    ):
        if isinstance(raw, str):
            add(as_text(raw))
        elif isinstance(raw, dict):
            add(as_text(raw.get("statement")), as_text(raw.get("reasoning")))

    return collected


def _collect_facts(
    company: dict[str, Any],
    customer: dict[str, Any],
    situation: dict[str, Any],
    context: dict[str, Any],
) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(key: str | None, value: str | None, value_type: str = "string") -> None:
        if not key or value is None or key in seen:
            return
        if _looks_like_belief(value):
            return
        seen.add(key)
        facts.append({"key": key, "value": value, "value_type": value_type})

    for raw in (
        *_as_list(company.get("facts")),
        *_as_list(customer.get("facts")),
        *_as_list(situation.get("facts")),
        *_as_list(context.get("facts")),
    ):
        if not isinstance(raw, dict):
            continue
        statement = as_text(raw.get("statement"))
        if statement and _looks_like_belief(statement):
            continue
        key = as_text(raw.get("key"))
        value = as_text(raw.get("value"))
        value_type = as_text(raw.get("value_type")) or "string"
        add(key, value, value_type)

    for source in (company, customer, situation):
        for key in ("paying_customers", "customer_count"):
            raw_value = source.get(key)
            if raw_value is None:
                continue
            add(key, str(raw_value).strip(), "number")

    return facts


def _collect_constraints(
    situation: dict[str, Any],
    context: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    raw_items = [
        *_as_list(situation.get("constraints")),
        *_as_list(context.get("constraints")),
    ]
    single = situation.get("constraint")
    if single is not None:
        raw_items.append(single)

    for raw in raw_items:
        if isinstance(raw, str):
            text = as_text(raw)
            if text:
                items.append(
                    {
                        "type": "other",
                        "name": "onboarding_constraint",
                        "description": text,
                        "severity": "medium",
                    }
                )
            continue
        if not isinstance(raw, dict):
            continue
        constraint_type = (as_text(raw.get("type")) or "other").lower()
        if constraint_type not in ALLOWED_CONSTRAINT_TYPES:
            constraint_type = "other"
        name = as_text(raw.get("name")) or constraint_type
        description = as_text(raw.get("description"))
        value = as_text(raw.get("value"))
        if not description and not value:
            continue
        items.append(
            {
                "type": constraint_type,
                "name": name,
                "description": description or name,
                "value": value or "",
                "severity": as_text(raw.get("severity")) or "medium",
            }
        )
    return items


async def confirm_onboarding(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    user: User,
) -> OnboardingDraft:
    result = await db.execute(
        select(OnboardingDraft)
        .where(OnboardingDraft.company_id == company_id)
        .with_for_update()
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise ConfirmError(404, "Onboarding draft not found")

    if draft.status == STATUS_CONFIRMED:
        return draft

    extracted = _validate_and_extract(draft.payload or {}, draft.current_step)
    company = await db.get(Company, company_id)
    if company is None:
        raise ConfirmError(403, "Not allowed to access this company")

    try:
        await _apply_brain(db, company=company, user=user, extracted=extracted)
        draft.status = STATUS_CONFIRMED
        draft.confirmed_at = utcnow()
        draft.confirmed_by_user_id = user.id
        await db.commit()
        await db.refresh(draft)
        return draft
    except ConfirmError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


async def _apply_brain(
    db: AsyncSession,
    *,
    company: Company,
    user: User,
    extracted: dict[str, Any],
) -> None:
    source_reference = onboarding_source_reference(company.id)

    company.name = extracted["name"]
    company.product_description = extracted["product_description"]
    company.target_customer = extracted["target_customer"]
    company.stage = extracted["stage"]
    if extracted["mission"]:
        company.mission = extracted["mission"]

    profile_result = await db.execute(
        select(CompanyBrainProfile).where(CompanyBrainProfile.company_id == company.id)
    )
    brain = profile_result.scalar_one_or_none()
    if brain is None:
        brain = CompanyBrainProfile(company_id=company.id, version=1)
        db.add(brain)
        await db.flush()

    if extracted["strategy"]:
        brain.strategy = extracted["strategy"]
    if extracted["non_goals"]:
        brain.non_goals = extracted["non_goals"]
    if extracted["current_priorities"]:
        brain.current_priorities = extracted["current_priorities"]
    if extracted["bottleneck"]:
        brain.current_bottlenecks = extracted["bottleneck"]
    if extracted["working_style"]:
        brain.working_style = extracted["working_style"]

    for fact in extracted["facts"]:
        await _ensure_fact(db, company.id, source_reference, fact)
    for belief in extracted["beliefs"]:
        await _ensure_belief(db, company.id, belief)
    for constraint in extracted["constraints"]:
        await _ensure_constraint(db, company.id, constraint)

    objective = await _ensure_objective(db, company.id, user.id, extracted)
    await _ensure_decision(db, company.id, user.id, objective.id if objective else None)


async def _ensure_fact(
    db: AsyncSession,
    company_id: uuid.UUID,
    source_reference: str,
    fact: dict[str, str],
) -> None:
    existing = await db.execute(
        select(CompanyFact).where(
            CompanyFact.company_id == company_id,
            CompanyFact.key == fact["key"],
            CompanyFact.source_reference == source_reference,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(
        CompanyFact(
            company_id=company_id,
            key=fact["key"],
            value=fact["value"],
            value_type=fact["value_type"],
            source_type=SOURCE_FOUNDER_INPUT,
            source_reference=source_reference,
            status="active",
        )
    )


async def _ensure_belief(
    db: AsyncSession, company_id: uuid.UUID, belief: dict[str, str]
) -> None:
    existing = await db.execute(
        select(CompanyBelief).where(
            CompanyBelief.company_id == company_id,
            CompanyBelief.statement == belief["statement"],
            CompanyBelief.source == SOURCE_FOUNDER_INPUT,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(
        CompanyBelief(
            company_id=company_id,
            statement=belief["statement"],
            reasoning=belief.get("reasoning"),
            status="active",
            source=SOURCE_FOUNDER_INPUT,
        )
    )


async def _ensure_constraint(
    db: AsyncSession, company_id: uuid.UUID, constraint: dict[str, str]
) -> None:
    existing = await db.execute(
        select(CompanyConstraint).where(
            CompanyConstraint.company_id == company_id,
            CompanyConstraint.type == constraint["type"],
            CompanyConstraint.name == constraint["name"],
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(
        CompanyConstraint(
            company_id=company_id,
            type=constraint["type"],
            name=constraint["name"],
            description=constraint.get("description"),
            value=constraint.get("value") or None,
            severity=constraint["severity"],
            status="active",
        )
    )


async def _ensure_objective(
    db: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    extracted: dict[str, Any],
) -> Objective | None:
    title = extracted["objective_title"]
    existing = await db.execute(
        select(Objective).where(
            Objective.company_id == company_id,
            Objective.title == title,
            Objective.created_by == user_id,
        )
    )
    found = existing.scalar_one_or_none()
    if found is not None:
        return found
    objective = Objective(
        company_id=company_id,
        title=title,
        description=extracted.get("objective_description"),
        status="active",
        priority="high",
        deadline=extracted.get("deadline"),
        created_by=user_id,
    )
    db.add(objective)
    await db.flush()
    return objective


async def _ensure_decision(
    db: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    objective_id: uuid.UUID | None,
) -> None:
    existing = await db.execute(
        select(Decision).where(
            Decision.company_id == company_id,
            Decision.title == ONBOARDING_DECISION_TITLE,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(
        Decision(
            company_id=company_id,
            objective_id=objective_id,
            title=ONBOARDING_DECISION_TITLE,
            decision="Founder confirmed the initial Company Brain from onboarding.",
            rationale=f"Confirmed via {onboarding_source_reference(company_id)}",
            status="active",
            created_by=user_id,
        )
    )
