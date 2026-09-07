import uuid
import hashlib
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role
from app.graph.neo4j_client import neo4j_client
from app.models.standards import StandardsUpload
from app.services.audit import record_audit
from app.services.standards_ingestor import ControlInput, parse_controls
router = APIRouter(prefix='/standards', tags=['standards'])
editor = require_role('Admin', 'ComplianceOfficer')

def persist(controls, filename, user, db):
    rows = []
    for c in controls:
        unknown = [aid for aid in c.asset_ids if neo4j_client.get_asset(aid) is None]
        if unknown: raise HTTPException(422, 'Unknown asset IDs: ' + ', '.join(unknown[:10]))
        key = hashlib.sha256((c.framework + '\0' + c.id).encode()).hexdigest()[:24]
        rows.append({**c.model_dump(), 'graph_id': 'control-' + key,
                     'framework_id': 'framework-' + hashlib.sha256(c.framework.encode()).hexdigest()[:24]})
    upload = StandardsUpload(uploaded_by=uuid.UUID(user['id']), file_name=filename[:255],
        file_type=filename.rsplit('.',1)[-1][:20], status='pending', controls_parsed=0)
    db.add(upload)
    db.commit()
    try:
        neo4j_client.run("""
          UNWIND $rows AS row
          MERGE (f:Framework {name: row.framework}) ON CREATE SET f.id = row.framework_id
          MERGE (c:Control {id: row.graph_id})
          SET c.name = row.name, c.reference = row.id, c.description = row.description,
              c.status = row.status, c.upload_id = $upload_id
          MERGE (c)-[:PART_OF]->(f)
          WITH c, row
          OPTIONAL MATCH (c)-[old:APPLIES_TO]->(:Asset)
          DELETE old
          WITH DISTINCT c, row
          UNWIND CASE WHEN size(row.asset_ids)=0 THEN [null] ELSE row.asset_ids END AS asset_id
          OPTIONAL MATCH (a:Asset {id: asset_id})
          FOREACH (_ IN CASE WHEN a IS NULL THEN [] ELSE [1] END | MERGE (c)-[:APPLIES_TO]->(a))
        """, {'rows': rows, 'upload_id': str(upload.id)})
        upload.status = 'processed'
        upload.controls_parsed = len(rows)
        record_audit(db, 'STANDARD_PROCESSED', user['id'], 'standard', str(upload.id))
        db.commit()
    except Exception:
        db.rollback()
        upload.status = 'failed'
        upload.error_message = 'Processing failed; review graph availability before retrying.'
        db.commit()
        raise HTTPException(503, 'Standard processing failed. Retry when the graph is available.')
    return {'id': str(upload.id), 'file_name': filename, 'status': upload.status, 'controls_parsed': len(rows)}

@router.post('/upload', status_code=201)
async def upload_standard(file: UploadFile=File(...), user=Depends(editor), db: Session=Depends(get_db)):
    content = await file.read(10 * 1024 * 1024 + 1)
    try: controls = parse_controls(file.filename or '', content)
    except Exception as exc:
        raise HTTPException(422, 'Invalid standard: ' + str(exc)[:500])
    return persist(controls, file.filename or 'upload', user, db)

@router.post('/controls', status_code=201)
def manual(control: ControlInput, user=Depends(editor), db: Session=Depends(get_db)):
    return persist([control], 'manual', user, db)

@router.get('')
def history(user=Depends(editor), db: Session=Depends(get_db)):
    return [{'id': str(r.id), 'file_name': r.file_name, 'status': r.status,
             'controls_parsed': r.controls_parsed, 'created_at': r.created_at}
            for r in db.query(StandardsUpload).order_by(StandardsUpload.created_at.desc()).limit(100)]
