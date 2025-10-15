from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
import uuid, logging
from fastapi import UploadFile, HTTPException, status
from app import models, schemas
from app.utils import azure_blob as blob_utils

logger = logging.getLogger(__name__)

PROJECTS_BASE = "projects"


# FILE URL ATTACHMENT HELPER
def _attach_file_urls(file: models.ProjectFile):
    """Attach API endpoints for download/preview to a ProjectFile."""
    if not hasattr(file, "download_url"):
        file.download_url = f"/blobs/download/{file.file_path}?base={PROJECTS_BASE}"
    if not hasattr(file, "preview_url"):
        file.preview_url = f"/blobs/preview/{file.file_path}?base={PROJECTS_BASE}"
    return file


# OWNERSHIP VERIFICATION
async def _verify_project_owner(db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID):
    """Ensure the project belongs to the current user."""
    result = await db.execute(
        select(models.Project).filter(
            models.Project.id == project_id,
            models.Project.owner_id == owner_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to this project",
        )
    return project


# PROJECTS CRUD
async def list_projects(db: AsyncSession, owner_id: uuid.UUID) -> List[models.Project]:
    """List all projects belonging to a specific user."""
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.files),
            selectinload(models.Project.company),
        )
        .filter(models.Project.owner_id == owner_id)
        .order_by(models.Project.created_at.desc())
    )
    projects = result.scalars().all()

    for p in projects:
        p.files = [_attach_file_urls(f) for f in p.files]

    logger.info(f" Listed {len(projects)} projects for owner {owner_id}")
    return projects


async def get_project(
    db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID
) -> Optional[models.Project]:
    """Get a single project with its files and company."""
    result = await db.execute(
        select(models.Project)
        .options(
            selectinload(models.Project.files),
            selectinload(models.Project.company),
        )
        .filter(models.Project.id == project_id, models.Project.owner_id == owner_id)
    )
    project = result.scalars().first()

    if project:
        project.files = [_attach_file_urls(f) for f in project.files]
        logger.info(f" Loaded project {project_id} for owner {owner_id}")
    else:
        logger.warning(f" Project {project_id} not found or access denied for owner {owner_id}")

    return project


async def create_project(
    db: AsyncSession,
    project: schemas.ProjectCreate,
    owner_id: uuid.UUID,
    files: Optional[List[UploadFile]] = None,
) -> models.Project:
    """Create a new project, optionally linked to a company, with file uploads."""
    # Validate company ownership (except Sigmoid default)
    if project.company_id:
        from app.utils import ratecards
        sigmoid = await ratecards.get_or_create_sigmoid_company(db)

        if project.company_id != sigmoid.id:
            result = await db.execute(
                select(models.Company).filter(
                    models.Company.id == project.company_id,
                    models.Company.owner_id == owner_id
                )
            )
            company = result.scalar_one_or_none()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not own this company.",
                )

    # Create and commit project
    db_project = models.Project(**project.dict(), owner_id=owner_id)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    logger.info(f" Created project {db_project.id} (owner={owner_id}, company={project.company_id})")

    # Attach files if provided
    if files:
        await add_project_files(db, db_project.id, files, owner_id)
        logger.info(f" Attached {len(files)} files to project {db_project.id}")

    # Refresh related data instead of extra SELECT
    await db.refresh(db_project, attribute_names=["company", "files"])
    db_project.files = [_attach_file_urls(f) for f in db_project.files]

    return db_project



async def update_project(
    db: AsyncSession,
    db_project: models.Project,
    update_data: schemas.ProjectBase,
) -> models.Project:
    """Update a project’s editable fields."""
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(db_project, field, value)
    await db.commit()
    await db.refresh(db_project)
    logger.info(f" Updated project {db_project.id}")
    return db_project

async def delete_project(db: AsyncSession, db_project: models.Project) -> bool:
    """Delete a single project (blob cleanup handled by SQLAlchemy event listeners)."""
    logger.info(f" Deleting project {db_project.id} ({len(db_project.files)} files)...")

    await db.delete(db_project)
    await db.commit()

    logger.info(f" Project {db_project.id} deleted successfully (DB + Blob folder auto-cleaned).")
    return True



async def delete_all_projects(db: AsyncSession, owner_id: uuid.UUID) -> int:
    """Delete all projects belonging to a user (DB + Blob cleanup via event listeners)."""
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.files))
        .filter(models.Project.owner_id == owner_id)
    )
    projects = result.scalars().all()
    count = len(projects)

    if not projects:
        logger.info(f" No projects found for owner {owner_id}")
        return 0

    logger.info(f" Deleting {count} projects for owner {owner_id}...")

    # Await async delete for each project
    for project in projects:
        await db.delete(project)

    await db.commit()

    logger.info(f" Deleted {count} projects for owner {owner_id} (DB + Blob folders auto-cleaned).")
    return count





# PROJECT FILES CRUD
async def add_project_file(
    db: AsyncSession,
    project_id: uuid.UUID,
    upload_file: Union[dict, UploadFile],
    owner_id: uuid.UUID,
) -> models.ProjectFile:
    """Add a single file to a project."""
    await _verify_project_owner(db, project_id, owner_id)

    if isinstance(upload_file, dict) and "file_path" in upload_file:
        db_file = models.ProjectFile(
            project_id=project_id,
            file_name=upload_file["file_name"],
            file_path=upload_file["file_path"],
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        return _attach_file_urls(db_file)

    # Handle new UploadFile objects
    safe_name = upload_file.filename.replace(" ", "_")
    unique_name = f"{PROJECTS_BASE}/{project_id}/{uuid.uuid4()}_{safe_name}"

    file_bytes = await upload_file.read()
    await blob_utils.upload_bytes(file_bytes, unique_name)

    db_file = models.ProjectFile(
        project_id=project_id,
        file_name=upload_file.filename,
        file_path=unique_name,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return _attach_file_urls(db_file)


async def add_project_files(
    db: AsyncSession,
    project_id: uuid.UUID,
    files: List[Union[dict, UploadFile]],
    owner_id: uuid.UUID,
) -> List[models.ProjectFile]:
    """Add multiple files to a project."""
    results = []
    for f in files:
        results.append(await add_project_file(db, project_id, f, owner_id))
    logger.info(f" Added {len(results)} files to project {project_id}")
    return results


async def list_project_files(
    db: AsyncSession,
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> List[models.ProjectFile]:
    """List all files for a given project owned by the user."""
    result = await db.execute(
        select(models.ProjectFile)
        .join(models.Project)
        .filter(
            models.ProjectFile.project_id == project_id,
            models.Project.owner_id == owner_id,
        )
        .order_by(models.ProjectFile.uploaded_at.desc())
    )
    files = result.scalars().all()
    return [_attach_file_urls(f) for f in files]


# FINALIZED SCOPE UTILITIES
async def has_finalized_scope(db: AsyncSession, project_id: uuid.UUID) -> bool:
    """Check whether a project has a finalized scope JSON file."""
    result = await db.execute(
        select(models.ProjectFile).filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json",
        )
    )
    exists = result.scalar_one_or_none() is not None
    logger.debug(f"🔍 Project {project_id} finalized scope exists={exists}")
    return exists
