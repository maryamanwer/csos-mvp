import uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_role
from app.models.standards import Report
from app.services.audit import record_audit
from app.services.reporting import report_rows, render_report
router = APIRouter(prefix='/reports', tags=['reports'])
reader = require_role('Admin', 'ComplianceOfficer', 'Executive')

def describe(report):
    return {'id': str(report.id), 'report_type': report.report_type, 'format': report.format,
            'created_at': report.created_at, 'status': 'completed'}

@router.post('/generate', status_code=201)
def generate_report(report_type: Literal['risk','compliance','asset'], format: Literal['pdf','xlsx']='pdf',
                    user=Depends(reader), db: Session=Depends(get_db)):
    report_id = uuid.uuid4()
    directory = Path(settings.REPORT_DIRECTORY).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{report_id}.{format}'
    try:
        rows = report_rows(report_type)
        render_report(path, report_type, format, rows)
        report = Report(id=report_id, generated_by=uuid.UUID(user['id']), report_type=report_type,
                        format=format, file_path=str(path))
        db.add(report)
        record_audit(db, 'REPORT_GENERATED', user['id'], 'report', str(report_id))
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return describe(report)

@router.get('')
def history(user=Depends(reader), db: Session=Depends(get_db)):
    return [describe(r) for r in db.query(Report).filter_by(generated_by=uuid.UUID(user['id']))
            .order_by(Report.created_at.desc()).limit(100).all()]

@router.get('/{report_id}/download')
def download(report_id: uuid.UUID, user=Depends(reader), db: Session=Depends(get_db)):
    report = db.query(Report).filter_by(id=report_id, generated_by=uuid.UUID(user['id'])).first()
    if not report: raise HTTPException(404, 'Report not found')
    path = Path(report.file_path).resolve()
    if path.parent != Path(settings.REPORT_DIRECTORY).resolve() or not path.is_file():
        raise HTTPException(404, 'Report file unavailable')
    media = 'application/pdf' if report.format == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return FileResponse(path, filename=f'csos-{report.report_type}.{report.format}', media_type=media)
