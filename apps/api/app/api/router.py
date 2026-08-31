from fastapi import APIRouter

from app.api.routes import (
    approvals,
    auth,
    brain,
    companies,
    evidence,
    head_agent,
    learnings,
    objective_tasks,
    objectives,
    onboarding,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(objectives.router)
api_router.include_router(objective_tasks.router)
api_router.include_router(onboarding.router)
api_router.include_router(brain.router)
api_router.include_router(evidence.router)
api_router.include_router(learnings.router)
api_router.include_router(head_agent.router)
api_router.include_router(approvals.router)
