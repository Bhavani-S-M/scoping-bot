import uuid, json, logging
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, status
)
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas, models
from app import crud as projects
from app.config.database import get_async_session
from app.utils import scope_engine, export, azure_blob
from app.auth.router import fastapi_users

get_current_active_user = fastapi_users.current_user(active=True)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


# List Projects
@router.get("", response_model=List[schemas.Project])
async def list_projects(
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    items = await projects.list_projects(db, owner_id=current_user.id)

    for p in items:
        p.has_finalized_scope = await projects.has_finalized_scope(db, p.id)

    return items


# Create Project + Auto Scope Preview
@router.post("", response_model=schemas.ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    name: Optional[str] = Form(None),
    domain: Optional[str] = Form(None),
    complexity: Optional[str] = Form(None),
    tech_stack: Optional[str] = Form(None),
    use_cases: Optional[str] = Form(None),
    compliance: Optional[str] = Form(None),
    duration: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_async_session),
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
    db_project = await projects.create_project(db, project_data, current_user.id, files)

    scope: Optional[schemas.GeneratedScopeResponse] = None
    try:
        logger.info(f"Generating scope for project {db_project.id}...")
        raw_scope = await scope_engine.generate_project_scope(db_project)
        normalized_scope = export.generate_json_data(raw_scope) or {}
        if normalized_scope:
            scope = schemas.GeneratedScopeResponse(**normalized_scope)
        logger.info(f"Scope generation completed for project {db_project.id}")
    except Exception as e:
        logger.error(f"Scope generation failed for {db_project.id}: {e}")

    return schemas.ProjectCreateResponse(
        project_id=db_project.id,
        scope=scope,
        redirect_url=f"/projects/{db_project.id}/export/json",
        has_finalized_scope=False 
    )


# Get Project Details
@router.get("/{project_id}", response_model=schemas.Project)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for f in project.files:
        f.download_url = f"/blobs/download/{f.file_path}?base=projects"
        f.preview_url = f"/blobs/preview/{f.file_path}?base=projects"

    project.has_finalized_scope = await projects.has_finalized_scope(db, project.id)

    return project


# Update Project
@router.put("/{project_id}", response_model=schemas.Project)
async def update_project(
    project_id: uuid.UUID,
    project_update: schemas.ProjectBase,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    return await projects.update_project(db, db_project, project_update)


# Delete Project
@router.delete("/{project_id}", response_model=schemas.MessageResponse)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    await projects.delete_project(db, db_project)
    return {"msg": "Project deleted successfully"}


# Delete All Projects
@router.delete("", response_model=schemas.MessageResponse)
async def delete_all_projects(
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    count = await projects.delete_all_projects(db, owner_id=current_user.id)
    return {"msg": f"Deleted {count} projects successfully"}


# Generate Scope
@router.get("/{project_id}/generate_scope", response_model=schemas.GeneratedScopeResponse)
async def generate_project_scope(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(f"Manually generating scope for project {db_project.id}...")
    raw_scope = await scope_engine.generate_project_scope(db_project)
    normalized_scope = export.generate_json_data(raw_scope)
    return schemas.GeneratedScopeResponse(**normalized_scope)


# Finalize Scope
@router.post("/{project_id}/finalize_scope", response_model=schemas.MessageResponse)
async def finalize_project_scope(
    project_id: uuid.UUID,
    scope_data: Dict[str, Any],
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_file, cleaned_scope = await projects.finalize_scope(db, db_project.id, scope_data)

    return {
        "msg": "Project scope finalized successfully",
        "scope": cleaned_scope,
        "file_url": azure_blob.get_blob_url(db_file.file_path),
        "has_finalized_scope": True
    }
