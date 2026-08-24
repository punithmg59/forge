"""ObjectiveTask read-only queries for founder operating view."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.objective_task import ObjectiveTask


async def list_objective_tasks(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> list[ObjectiveTask]:
    result = await db.execute(
        select(ObjectiveTask)
        .where(ObjectiveTask.company_id == company_id)
        .order_by(ObjectiveTask.created_at.desc())
    )
    return list(result.scalars().all())
