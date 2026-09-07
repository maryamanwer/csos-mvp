from fastapi import APIRouter

from app.api.v1 import (
    admin,
    assets,
    auth,
    chat,
    compliance,
    dashboard,
    reports,
    risk,
    standards,
    topology,
    vulnerabilities,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(assets.router)
api_router.include_router(risk.router)
api_router.include_router(compliance.router)
api_router.include_router(standards.router)
api_router.include_router(chat.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(topology.router)
api_router.include_router(vulnerabilities.router)
api_router.include_router(dashboard.router)

from app.api.v1 import ai
api_router.include_router(ai.router)

from app.api.v1 import workflows
api_router.include_router(workflows.router)
