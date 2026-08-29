from fastapi import APIRouter

from app.api.v1 import admin, ai_models, assets, auth, chat, compliance
from app.api.v1 import connectors, dashboard, findings, ingest, reports
from app.api.v1 import risk, standards, topology, vulnerabilities

api_router = APIRouter(prefix="/api/v1")
for route_group in (
    auth, assets, risk, compliance, standards, chat, reports, admin, topology,
    vulnerabilities, dashboard, findings, connectors, ingest, ai_models,
):
    api_router.include_router(route_group.router)
