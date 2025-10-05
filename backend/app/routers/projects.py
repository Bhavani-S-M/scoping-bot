import uuid, json, logging
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select 

from app import schemas, models
from app import crud as projects
from app.config.database import get_async_session
from app.utils import scope_engine, azure_blob
from app.auth.router import fastapi_users

get_current_active_user = fastapi_users.current_user(active=True)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["Projects"])


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


# Create Project
@router.post("", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
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
    if not any([name, domain, complexity, tech_stack, use_cases, compliance, duration, files]):
        raise HTTPException(
            status_code=400,
            detail="At least one project field or file must be provided."
        )

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
    db_project.has_finalized_scope = False
    return db_project


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
async def generate_project_scope_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    # Fetch the project
    db_project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate full scope (includes architecture)
    scope = await scope_engine.generate_project_scope(db, db_project) or {}

    return schemas.GeneratedScopeResponse(
        overview=scope.get("overview", {}),
        activities=scope.get("activities", []),
        resourcing_plan=scope.get("resourcing_plan", []),
        architecture_diagram=scope.get("architecture_diagram")
    )



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

    db_file, cleaned_scope = await scope_engine.finalize_scope(db, db_project.id, scope_data)
    return {
        "msg": "Project scope finalized successfully",
        "scope": cleaned_scope,
        "file_url": azure_blob.get_blob_url(db_file.file_path),
        "has_finalized_scope": True
    }

# -------------------------
# Get Finalized Scope
# -------------------------
@router.get("/{project_id}/finalized_scope")
async def get_finalized_scope(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(models.ProjectFile).filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json"
        )
    )
    db_file = result.scalars().first()

    if not db_file:
        # ✅ Return gracefully instead of 404
        return None  # or: return {"has_finalized_scope": False, "scope": None}

    try:
        blob_bytes = await azure_blob.download_bytes(db_file.file_path)
        scope_data = json.loads(blob_bytes.decode("utf-8"))
        return scope_data
    except Exception as e:
        logger.error(f"Failed to fetch finalized scope: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch finalized scope")



# -------------------------
# Regenerate Scope
# -------------------------
@router.post("/{project_id}/regenerate_scope", response_model=schemas.GeneratedScopeResponse)
async def regenerate_scope_with_instructions(
    project_id: uuid.UUID,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
):
    db_project = await projects.get_project(db, project_id=project_id, owner_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    draft = payload.get("draft")
    instructions = payload.get("instructions", "")

    if not draft:
        raise HTTPException(status_code=400, detail="Missing draft scope")

    try:
        logger.info(f"Regenerating scope for project {project_id} with user instructions...")
        regen_scope = await scope_engine.regenerate_from_instructions(draft, instructions) or {}
        return schemas.GeneratedScopeResponse(**regen_scope)
    except Exception as e:
        logger.error(f"Scope regeneration failed for {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Scope regeneration failed")
