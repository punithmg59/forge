from __future__ import annotations

import re
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.user import User

ROLE_FOUNDER = "founder"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
VALID_ROLES = frozenset({ROLE_FOUNDER, ROLE_ADMIN, ROLE_MEMBER})
COMPANY_MANAGE_ROLES = frozenset({ROLE_FOUNDER})


def slugify_company_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = slug[:40] or "company"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


async def create_company(
    db: AsyncSession,
    *,
    user: User,
    name: str,
    description: str | None,
    target_customer: str | None,
    stage: str | None,
) -> Company:
    company = Company(
        name=name.strip(),
        slug=slugify_company_name(name),
        product_description=description.strip() if description else None,
        target_customer=target_customer.strip() if target_customer else None,
        stage=stage.strip() if stage else None,
    )
    db.add(company)
    await db.flush()

    membership = CompanyMember(
        company_id=company.id,
        user_id=user.id,
        role=ROLE_FOUNDER,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(company)
    return company


async def list_companies_for_user(db: AsyncSession, user_id: uuid.UUID) -> Sequence[Company]:
    result = await db.execute(
        select(Company)
        .join(CompanyMember, CompanyMember.company_id == Company.id)
        .where(CompanyMember.user_id == user_id)
        .order_by(Company.created_at.desc())
    )
    return result.scalars().all()


async def get_company(db: AsyncSession, company_id: uuid.UUID) -> Company | None:
    return await db.get(Company, company_id)


async def get_membership(
    db: AsyncSession, *, user_id: uuid.UUID, company_id: uuid.UUID
) -> CompanyMember | None:
    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.user_id == user_id,
            CompanyMember.company_id == company_id,
        )
    )
    return result.scalar_one_or_none()


async def update_company(
    db: AsyncSession,
    company: Company,
    *,
    name: str | None = None,
    description: str | None = None,
    target_customer: str | None = None,
    stage: str | None = None,
) -> Company:
    if name is not None:
        company.name = name.strip()
    if description is not None:
        company.product_description = description.strip() or None
    if target_customer is not None:
        company.target_customer = target_customer.strip() or None
    if stage is not None:
        company.stage = stage.strip() or None
    await db.commit()
    await db.refresh(company)
    return company


async def list_members(db: AsyncSession, company_id: uuid.UUID) -> list[tuple[CompanyMember, User]]:
    result = await db.execute(
        select(CompanyMember, User)
        .join(User, User.id == CompanyMember.user_id)
        .where(CompanyMember.company_id == company_id)
        .order_by(CompanyMember.created_at.asc())
    )
    return list(result.all())
