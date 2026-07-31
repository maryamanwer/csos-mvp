"""
Reporting endpoints (PDF/Excel export).
TODO(P4): implement PDF generation via reportlab and Excel via openpyxl,
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
    # TODO(P4): real generation; for now return a scaffold descriptor
    return {"report_type": report_type, "format": format, "status": "queued"}
