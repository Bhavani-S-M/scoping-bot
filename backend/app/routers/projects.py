"""
Project router: handles project CRUD and AI scoping.
"""
import uuid, json, logging
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, status
)
from sqlalchemy.orm import Session

from app import schemas, models
from app import crud as projects
from app.config.database import get_db
from app.utils import scope_engine, export, azure_blob
from app.auth.router import fastapi_users

# Dependency
get_current_active_user = fastapi_users.current_user(active=True)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


#  List Projects 
@router.get("/", response_model=List[schemas.Project])
def list_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    return projects.list_projects(db, owner_id=current_user.id)


# Create Project + Auto Scope Preview
# Create Project + Auto Scope Preview
@router.post("/", response_model=schemas.ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    name: Optional[str] = Form(None),
    domain: Optional[str] = Form(None),
    complexity: Optional[str] = Form(None),
    tech_stack: Optional[str] = Form(None),
    use_cases: Optional[str] = Form(None),
    compliance: Optional[str] = Form(None),
    duration: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    project_data = schemas.ProjectCreate(
        name=name.strip() if name else None,
        domain=domain,
        complexity=complexity,
        tech_stack=tech_stack,
        use_cases=use_cases,
        compliance=compliance,
        duration=duration,
    )
    db_project = projects.create_project(db, project_data, current_user.id, files)

    scope: Optional[schemas.GeneratedScopeResponse]
    try:
        raw_scope = scope_engine.generate_project_scope(db_project)
        normalized_scope = export.generate_json_data(raw_scope) or {}
        # only build response if we have something
        if normalized_scope:
            scope = schemas.GeneratedScopeResponse(**normalized_scope)
    except Exception as e:
        logger.error(f"Scope generation failed: {e}")

    return schemas.ProjectCreateResponse(
        project_id=db_project.id,
        scope=scope, 
        redirect_url=f"/projects/{db_project.id}/export/json"
    )


# Get Project Details
@router.get("/{project_id}", response_model=schemas.Project)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    project = projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # enrich file objects with URLs
    for f in project.files:
        f.download_url = f"/blobs/download/{f.file_path}?base=projects"
        f.preview_url = f"/blobs/preview/{f.file_path}?base=projects"

    return project


# Update Project
@router.put("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: uuid.UUID,
    project_update: schemas.ProjectBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    return projects.update_project(db, db_project, project_update)


# Delete Project
@router.delete("/{project_id}", response_model=schemas.MessageResponse)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    projects.delete_project(db, db_project)
    return {"msg": "Project deleted successfully"}


# Delete All Projects
@router.delete("/", response_model=schemas.MessageResponse)
def delete_all_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    count = projects.delete_all_projects(db, owner_id=current_user.id)
    return {"msg": f"Deleted {count} projects successfully"}


# Generate Scope
@router.get("/{project_id}/generate_scope", response_model=schemas.GeneratedScopeResponse)
def generate_project_scope(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    raw_scope = scope_engine.generate_project_scope(db_project)
    normalized_scope = export.generate_json_data(raw_scope)
    return schemas.GeneratedScopeResponse(**normalized_scope)


# Finalize Scope
@router.post("/{project_id}/finalize_scope", response_model=schemas.MessageResponse)
def finalize_project_scope(
    project_id: uuid.UUID,
    scope_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_file, cleaned_scope = projects.finalize_scope(db, db_project.id, scope_data)

    return {
        "msg": "Project scope finalized successfully",
        "scope": cleaned_scope,
        "file_url": azure_blob.get_blob_url(db_file.file_path)
    }
