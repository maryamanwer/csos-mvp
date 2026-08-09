"""Vulnerability repository CRUD, filtering, asset linking, and bulk import."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.schemas.asset import BulkImportError, BulkImportResult
from app.schemas.vulnerability import (
    VulnerabilityCreate,
    VulnerabilityOut,
    VulnerabilityUpdate,
)
from app.services.audit import record_audit
from app.services.imports import parse_tabular_upload

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])
READ_ROLES = ("Admin", "Engineer", "Analyst", "Executive")
WRITE_ROLES = ("Admin", "Analyst", "Engineer")


@router.get("", response_model=list[VulnerabilityOut])
def list_vulnerabilities(
    search: str | None = Query(default=None, max_length=100),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    asset_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_role(*READ_ROLES)),
):
    return neo4j_client.list_vulnerabilities(
        search=search,
        severity=severity,
        status=status_filter,
        asset_id=asset_id,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=VulnerabilityOut, status_code=status.HTTP_201_CREATED)
def create_vulnerability(
    payload: VulnerabilityCreate,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    properties = payload.model_dump(exclude={"asset_ids"})
    vulnerability = neo4j_client.create_vulnerability(properties, payload.asset_ids)
    record_audit(
        db,
        "VULNERABILITY_CREATED",
        user_id=current_user["id"],
        entity_type="Vulnerability",
        entity_id=vulnerability["id"],
        metadata={"title": vulnerability["title"]},
    )
    db.commit()
    return vulnerability


@router.post("/import", response_model=BulkImportResult)
async def import_vulnerabilities(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    try:
        rows = parse_tabular_upload(file.filename or "vulnerabilities.csv", await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    imported = 0
    errors: list[BulkImportError] = []
    for index, row in enumerate(rows, start=2):
        try:
            asset_ids = row.pop("asset_ids", [])
            if isinstance(asset_ids, str):
                asset_ids = [item.strip() for item in asset_ids.split(",") if item.strip()]
            data_sources = row.get("data_sources", [])
            if isinstance(data_sources, str):
                data_sources = [item.strip() for item in data_sources.split(",") if item.strip()]
            normalized = {
                **row,
                "severity": str(row.get("severity", "")).strip().lower(),
                "status": str(row.get("status", "open")).strip().lower(),
                "asset_ids": asset_ids,
                "data_sources": data_sources,
            }
            vulnerability = VulnerabilityCreate.model_validate(normalized)
            neo4j_client.create_vulnerability(
                vulnerability.model_dump(exclude={"asset_ids"}),
                vulnerability.asset_ids,
            )
            imported += 1
        except (ValidationError, ValueError) as exc:
            errors.append(BulkImportError(row=index, message=str(exc)))
    record_audit(
        db,
        "VULNERABILITY_IMPORT",
        user_id=current_user["id"],
        entity_type="Vulnerability",
        metadata={"file": file.filename, "imported": imported, "failed": len(errors)},
    )
    db.commit()
    return BulkImportResult(imported=imported, failed=len(errors), errors=errors[:50])


@router.get("/{vulnerability_id}", response_model=VulnerabilityOut)
def get_vulnerability(
    vulnerability_id: str,
    user: dict = Depends(require_role(*READ_ROLES)),
):
    vulnerability = neo4j_client.get_vulnerability(vulnerability_id)
    if not vulnerability:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vulnerability


@router.put("/{vulnerability_id}", response_model=VulnerabilityOut)
def update_vulnerability(
    vulnerability_id: str,
    payload: VulnerabilityUpdate,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    values = payload.model_dump(exclude_unset=True)
    asset_ids = values.pop("asset_ids", None)
    vulnerability = neo4j_client.update_vulnerability(
        vulnerability_id,
        values,
        asset_ids,
    )
    if not vulnerability:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    record_audit(
        db,
        "VULNERABILITY_UPDATED",
        user_id=current_user["id"],
        entity_type="Vulnerability",
        entity_id=vulnerability_id,
        metadata={"fields": sorted(payload.model_fields_set)},
    )
    db.commit()
    return vulnerability


@router.delete("/{vulnerability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vulnerability(
    vulnerability_id: str,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    if not neo4j_client.delete_vulnerability(vulnerability_id):
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    record_audit(
        db,
        "VULNERABILITY_DELETED",
        user_id=current_user["id"],
        entity_type="Vulnerability",
        entity_id=vulnerability_id,
    )
    db.commit()
