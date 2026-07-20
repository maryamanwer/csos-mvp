"""
Reporting endpoints (PDF/Excel export).
TODO(M4): implement PDF generation via reportlab and Excel via openpyxl,
persist metadata to the `reports` table, and store files on disk/volume.
"""
from fastapi import APIRouter, Depends

from app.core.security import require_role

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate")
def generate_report(
    report_type: str,
    format: str = "pdf",
    user: dict = Depends(require_role("Admin", "ComplianceOfficer", "Executive")),
):
    # TODO(M4): real generation; for now return a stub descriptor
    return {"report_type": report_type, "format": format, "status": "queued"}
