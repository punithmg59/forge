"""Shared test seed helpers."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.evidence import Evidence
from app.models.objective import Objective
from app.models.user import User


async def seed_company_with_evidence(
    session: AsyncSession,
    *,
    name: str,
    evidence_title: str = "Customer interview",
    evidence_content: str = "Founders prefer CLI tools.",
) -> tuple[CompanyMember, Company, Objective, Evidence]:
    user = User(email=f"tool-{uuid.uuid4()}@example.com", name="Tool Tester")
    session.add(user)
    await session.flush()
    company = Company(
        name=name,
        slug=f"tool-{uuid.uuid4().hex[:8]}",
        stage="mvp",
        mission="Build Forge",
    )
    session.add(company)
    await session.flush()
    membership = CompanyMember(
        company_id=company.id,
        user_id=user.id,
        role="founder",
    )
    objective = Objective(
        company_id=company.id,
        title="Grow customers",
        status="active",
        priority="300",
        created_by=user.id,
    )
    evidence = Evidence(
        company_id=company.id,
        type="interview",
        title=evidence_title,
        content=evidence_content,
        source_type="manual",
    )
    session.add(membership)
    session.add(objective)
    session.add(evidence)
    await session.flush()
    return membership, company, objective, evidence
