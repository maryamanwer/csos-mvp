"""Neo4j-backed asset inventory, imports, and relationship management."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.schemas.asset import (
    AssetCreate,
    AssetOut,
    AssetRelationship,
    AssetRelationshipCreate,
    AssetUpdate,
    BulkImportError,
    BulkImportResult,
)
from app.services.audit import record_audit
from app.services.imports import parse_tabular_upload

router = APIRouter(prefix="/assets", tags=["assets"])
READ_ROLES = ("Admin", "Engineer", "Analyst", "Executive", "ComplianceOfficer")
WRITE_ROLES = ("Admin", "Engineer")


@router.get("", response_model=list[AssetOut])
def list_assets(
    search: str | None = Query(default=None, max_length=100),
    asset_type: str | None = Query(default=None),
    criticality: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_role(*READ_ROLES)),
):
    return neo4j_client.list_assets(
        search=search,
        asset_type=asset_type,
        criticality=criticality,
        environment=environment,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    asset = neo4j_client.create_asset(payload.model_dump())
    record_audit(
        db,
        "ASSET_CREATED",
        user_id=current_user["id"],
        entity_type="Asset",
        entity_id=asset["id"],
        metadata={"name": asset["name"]},
    )
    db.commit()
    return asset


@router.post("/import", response_model=BulkImportResult)
async def import_assets(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    try:
        rows = parse_tabular_upload(file.filename or "assets.csv", await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    errors: list[BulkImportError] = []
    imported = 0
    for index, row in enumerate(rows, start=2):
        try:
            data_sources = row.get("data_sources", [])
            if isinstance(data_sources, str):
                data_sources = [item.strip() for item in data_sources.split(",") if item.strip()]
            normalized = {
                **row,
                "type": str(row.get("type", "")).strip().lower().replace(" ", "_"),
                "criticality": str(row.get("criticality", "")).strip().lower(),
                "data_sources": data_sources,
            }
            asset = AssetCreate.model_validate(normalized)
            neo4j_client.create_asset(asset.model_dump())
            imported += 1
        except (ValidationError, ValueError) as exc:
            errors.append(BulkImportError(row=index, message=str(exc)))
    record_audit(
        db,
        "ASSET_IMPORT",
        user_id=current_user["id"],
        entity_type="Asset",
        metadata={"file": file.filename, "imported": imported, "failed": len(errors)},
    )
    db.commit()
    return BulkImportResult(imported=imported, failed=len(errors), errors=errors[:50])


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: str,
    user: dict = Depends(require_role(*READ_ROLES)),
):
    asset = neo4j_client.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: str,
    payload: AssetUpdate,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    properties = payload.model_dump(exclude_unset=True)
    asset = neo4j_client.update_asset(asset_id, properties)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    record_audit(
        db,
        "ASSET_UPDATED",
        user_id=current_user["id"],
        entity_type="Asset",
        entity_id=asset_id,
        metadata={"fields": sorted(properties)},
    )
    db.commit()
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: str,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    if not neo4j_client.delete_asset(asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    record_audit(
        db,
        "ASSET_DELETED",
        user_id=current_user["id"],
        entity_type="Asset",
        entity_id=asset_id,
    )
    db.commit()


@router.post("/{asset_id}/relationships", response_model=AssetRelationship)
def create_relationship(
    asset_id: str,
    payload: AssetRelationshipCreate,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    relationship = neo4j_client.create_asset_relationship(
        asset_id,
        payload.target_id,
        payload.relationship_type,
        payload.properties,
    )
    if not relationship:
        raise HTTPException(status_code=404, detail="Source or target asset not found")
    record_audit(
        db,
        "ASSET_RELATIONSHIP_CREATED",
        user_id=current_user["id"],
        entity_type="AssetRelationship",
        entity_id=relationship["id"],
        metadata={
            "source_id": asset_id,
            "target_id": payload.target_id,
            "type": payload.relationship_type,
        },
    )
    db.commit()
    return AssetRelationship(**relationship)


@router.delete(
    "/{asset_id}/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_relationship(
    asset_id: str,
    relationship_id: str,
    current_user: dict = Depends(require_role(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    if not neo4j_client.delete_asset_relationship(relationship_id):
        raise HTTPException(status_code=404, detail="Relationship not found")
    record_audit(
        db,
        "ASSET_RELATIONSHIP_DELETED",
        user_id=current_user["id"],
        entity_type="AssetRelationship",
        entity_id=relationship_id,
        metadata={"asset_id": asset_id},
    )
    db.commit()
