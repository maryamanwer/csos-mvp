"""
Custom Standards & Policies upload endpoints.
Accepts CSV / Excel / Word / JSON / manual entry, normalizes, and
maps controls into the Knowledge Graph.
TODO(P4): implement parsers in app/services/standards_ingestor.py
for each file type and persist parsed controls to Neo4j.
"""
from fastapi import APIRouter, Depends, File, UploadFile

from app.core.security import require_role
from app.schemas.risk_compliance import ComplianceFrameworkCoverage  # placeholder import

router = APIRouter(prefix="/standards", tags=["standards"])


@router.post("/upload")
async def upload_standard(
    file: UploadFile = File(...),
    user: dict = Depends(require_role("Admin", "ComplianceOfficer")),
):
    # TODO(P4): route to the right parser based on file.content_type / extension
    # (csv -> pandas, xlsx -> openpyxl, docx -> python-docx, json -> json.loads)
    contents = await file.read()
    return {
        "file_name": file.filename,
        "size_bytes": len(contents),
        "status": "received",  # becomes "processed" when Phase 4 parsing is wired
    }
