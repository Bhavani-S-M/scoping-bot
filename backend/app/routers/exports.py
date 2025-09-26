import uuid, os, json, re, logging
from typing import Any, Dict, Optional
from app.utils import azure_blob

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models
from app import crud as projects
from app.config.database import get_db
from app.auth.router import fastapi_users
from app.utils import export
from app.utils import scope_engine 

current_active_user = fastapi_users.current_user(active=True)

router = APIRouter(prefix="/projects/{project_id}/export", tags=["Export"])


# ---------- Helpers ----------
def _get_project(project_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> models.Project:
    project = projects.get_project(db, project_id=project_id, owner_id=user_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return project


def _load_finalized_scope(project: models.Project) -> Optional[Dict[str, Any]]:
    """Try to fetch finalized scope JSON from blob storage."""
    for f in project.files:
        if f.file_name == "finalized_scope.json":
            try:
                blob_bytes = azure_blob.download_bytes(f.file_path)
                return json.loads(blob_bytes.decode("utf-8"))
            except Exception as e:
                logging.warning(f"Failed to load finalized scope from blob {f.file_path}: {e}")
                return None
    return None


def _safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", (name or "").strip().lower())


def _ensure_scope(project: models.Project) -> Dict[str, Any]:
    """Return finalized scope if available, else generate draft scope."""
    scope = _load_finalized_scope(project)
    if not scope:
        raw_scope = scope_engine.generate_project_scope(project)
        scope = export.generate_json_data(raw_scope or {})
    return scope


# PREVIEW EXPORTS (no DB)

@router.post("/preview/json")
def preview_json_from_scope(
    project_id: uuid.UUID,
    scope: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(current_active_user),
):
    project = _get_project(project_id, current_user.id, db)
    finalized = _load_finalized_scope(project)
    if (not scope or len(scope) == 0) and finalized:
        return finalized
    return export.generate_json_data(scope or {})


@router.post("/preview/excel")
def preview_excel_from_scope(
    project_id: uuid.UUID,
    scope: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(current_active_user),
):
    project = _get_project(project_id, current_user.id, db)
    finalized = _load_finalized_scope(project)
    normalized = export.generate_json_data(scope or {}) if not finalized else finalized
    file = export.generate_xlsx(normalized)
    safe_name = _safe_filename(normalized.get("overview", {}).get("Project Name") or f"project_{project_id}")
    return StreamingResponse(
        file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_{project_id}_preview.xlsx"},
    )


@router.post("/preview/pdf")
def preview_pdf_from_scope(
    project_id: uuid.UUID,
    scope: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(current_active_user),
):
    project = _get_project(project_id, current_user.id, db)
    finalized = _load_finalized_scope(project)
    normalized = export.generate_json_data(scope or {}) if not finalized else finalized
    file = export.generate_pdf(normalized)
    safe_name = _safe_filename(normalized.get("overview", {}).get("Project Name") or f"project_{project_id}")
    return StreamingResponse(
        file,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_{project_id}_preview.pdf"},
    )


# FINALIZED EXPORTS (with fallback)

@router.get("/json")
def export_project_json(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(current_active_user),
):
    project = _get_project(project_id, current_user.id, db)
    scope = _ensure_scope(project)
    return scope


@router.get("/excel")
def export_project_excel(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(current_active_user),
):
    project = _get_project(project_id, current_user.id, db)
    scope = _ensure_scope(project)
    file = export.generate_xlsx(scope)
    safe_name = _safe_filename(project.name or f"project_{project.id}")
    return StreamingResponse(
        file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_{project.id}.xlsx"},
    )


@router.get("/pdf")
def export_project_pdf(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(current_active_user),
):
    project = _get_project(project_id, current_user.id, db)
    scope = _ensure_scope(project)
    file = export.generate_pdf(scope)
    safe_name = _safe_filename(project.name or f"project_{project.id}")
    return StreamingResponse(
        file,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_{project.id}.pdf"},
    )
