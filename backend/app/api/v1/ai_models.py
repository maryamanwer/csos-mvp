"""Local/air-gapped AI runtime health and model lifecycle."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.ai.providers import resolve_model
from app.core.config import settings
from app.core.security import require_role

router = APIRouter(prefix="/ai/models", tags=["ai-models"])
VIEW_ROLES = ("Admin", "Engineer", "Analyst", "Executive", "ComplianceOfficer")


class ModelAction(BaseModel):
    model: str


def _installed_models(payload: dict) -> list[str]:
    names: list[str] = []
    for item in payload.get("models", []):
        name = item.get("name") or item.get("model")
        if name:
            names.append(str(name))
    return names


@router.get("/status")
def model_status(user: dict = Depends(require_role(*VIEW_ROLES))):
    installed: list[str] = []
    error: str | None = None
    try:
        response = httpx.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=5)
        response.raise_for_status()
        installed = _installed_models(response.json())
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    return {
        "provider": settings.AI_PROVIDER,
        "runtime": "ollama",
        "runtime_url": settings.OLLAMA_BASE_URL,
        "healthy": error is None,
        "default_model": settings.AI_DEFAULT_MODEL,
        "configured_models": list(settings.available_ai_models),
        "installed_models": installed,
        "error": error,
        "air_gapped_ready": True,
    }


@router.post("/pull")
def pull_model(
    payload: ModelAction,
    user: dict = Depends(require_role("Admin")),
):
    model = resolve_model(payload.model)
    try:
        response = httpx.post(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/pull",
            json={"name": model, "stream": False},
            timeout=1800,
        )
        response.raise_for_status()
        return {"model": model, "status": "installed"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Ollama model pull failed: {exc}") from exc


@router.post("/validate")
def validate_model(
    payload: ModelAction,
    user: dict = Depends(require_role("Admin", "Engineer")),
):
    model = resolve_model(payload.model)
    try:
        response = httpx.post(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            json={"model": model, "prompt": "Reply with CSOS-OK", "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return {"model": model, "status": "ready", "response": response.json().get("response", "")}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Model validation failed: {exc}") from exc
