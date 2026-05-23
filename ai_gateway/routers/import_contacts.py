"""
FastAPI endpoints for CSV import, CRM sync, and Marketo migration.
Mount at: /api/contacts and /api/integrations
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import uuid
from sqlalchemy import create_engine, text
import os

router = APIRouter()
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL) if DB_URL else None

# ─── CSV Import ──────────────────────────────────────────────
class ImportConfig(BaseModel):
    on_conflict: Literal["update", "skip", "error"] = "update"

@router.post("/import")
async def import_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    on_conflict: str = "update",
):
    """Upload a CSV and import contacts with deduplication."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files supported")

    content  = await file.read()
    job_id   = str(uuid.uuid4())

    # Create job record
    if engine:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO csv_import_jobs (id, filename, status, on_conflict, created_at)
                VALUES (:id, :fn, 'processing', :oc, NOW())
            """), {"id": job_id, "fn": file.filename, "oc": on_conflict})
            conn.commit()

    # Run import in background
    background_tasks.add_task(_run_csv_import, job_id, content, on_conflict)
    return {"job_id": job_id, "status": "processing", "filename": file.filename}

@router.get("/import/{job_id}")
async def get_import_status(job_id: str):
    """Poll import job status."""
    if not engine:
        raise HTTPException(503, "Database unavailable")
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM csv_import_jobs WHERE id = :id"), {"id": job_id}
        ).fetchone()
    if not row:
        raise HTTPException(404, "Import job not found")
    return dict(row._mapping)

async def _run_csv_import(job_id: str, content: bytes, on_conflict: str):
    from integrations.csv_import.importer import parse_csv, deduplicate_contacts, upsert_contacts_to_db, apply_tags_from_import
    rows, headers  = parse_csv(content)
    deduped        = deduplicate_contacts(rows)
    result         = upsert_contacts_to_db(deduped, on_conflict=on_conflict)
    apply_tags_from_import(deduped)

    if engine:
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE csv_import_jobs SET
                    status = 'completed', total_rows = :total, inserted = :ins,
                    updated = :upd, invalid_rows = :inv,
                    duplicates_in_csv = :dcsv, duplicates_in_db = :ddb,
                    errors = :errors::jsonb, completed_at = NOW()
                WHERE id = :id
            """), {
                "id":    job_id,
                "total": result.total_rows,
                "ins":   result.inserted,
                "upd":   result.updated,
                "inv":   result.invalid_rows,
                "dcsv":  result.duplicates_in_csv,
                "ddb":   result.duplicates_in_db,
                "errors": str(result.sample_errors[:5]),
            })
            conn.commit()


# ─── CRM Sync Triggers ───────────────────────────────────────
@router.post("/integrations/sync/salesforce")
async def trigger_sf_sync(background_tasks: BackgroundTasks):
    from integrations.salesforce.adapter import pull_from_salesforce
    background_tasks.add_task(pull_from_salesforce.delay)
    return {"status": "queued", "crm": "salesforce", "direction": "pull"}

@router.post("/integrations/sync/hubspot")
async def trigger_hs_sync(background_tasks: BackgroundTasks):
    from integrations.hubspot.adapter import pull_from_hubspot
    background_tasks.add_task(pull_from_hubspot.delay)
    return {"status": "queued", "crm": "hubspot", "direction": "pull"}

@router.post("/integrations/migrate/marketo")
async def trigger_marketo_migration(background_tasks: BackgroundTasks):
    """Start a full Marketo → OpenEngage migration job."""
    from integrations.marketo_migration.migrate import run_full_migration
    import asyncio
    background_tasks.add_task(asyncio.run, run_full_migration())
    return {"status": "started", "message": "Marketo migration running in background"}
