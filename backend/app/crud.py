from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
import uuid, logging, json
from fastapi import UploadFile
from app import models, schemas
from app.utils import azure_blob as blob_utils

logger = logging.getLogger(__name__)

# Constants
PROJECTS_BASE = "projects"


# Projects CRUD
async def list_projects(db: AsyncSession, owner_id: uuid.UUID) -> List[models.Project]:
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.files))
        .filter(models.Project.owner_id == owner_id)
        .order_by(models.Project.created_at.desc())
    )
    projects = result.scalars().all()
    logger.info(f"📂 Listed {len(projects)} projects for owner {owner_id}")
    return projects


async def get_project(
    db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID
) -> Optional[models.Project]:
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.files))
        .filter(models.Project.id == project_id, models.Project.owner_id == owner_id)
    )
    project = result.scalars().first()
    if project:
        logger.info(f"Loaded project {project_id} for owner {owner_id}")
    else:
        logger.warning(f" Project {project_id} not found or access denied for owner {owner_id}")
    return project


async def create_project(
    db: AsyncSession,
    project: schemas.ProjectCreate,
    owner_id: uuid.UUID,
    files: Optional[List[UploadFile]] = None
) -> models.Project:
    db_project = models.Project(**project.dict(), owner_id=owner_id)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    logger.info(f" Created project {db_project.id} for owner {owner_id}")

    if files:
        await add_project_files(db, db_project.id, files)
        logger.info(f" Attached {len(files)} files to project {db_project.id}")

    return db_project


async def update_project(
    db: AsyncSession,
    db_project: models.Project,
    update_data: schemas.ProjectBase
) -> models.Project:
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(db_project, field, value)
    await db.commit()
    await db.refresh(db_project)
    logger.info(f" Updated project {db_project.id}")
    return db_project


async def delete_project(db: AsyncSession, db_project: models.Project) -> bool:
    await db.refresh(db_project, attribute_names=["files"])

    logger.info(f"🗑 Deleting project {db_project.id} and {len(db_project.files)} attached files...")
    for f in db_project.files:
        try:
            if f.file_path:
                await blob_utils.delete_blob(f.file_path)
                logger.info(f" Deleted blob: {f.file_path}")
        except Exception as e:
            logger.warning(f" Failed to delete blob {f.file_path}: {e}")

    await db.delete(db_project)
    await db.commit()
    logger.info(f" Project {db_project.id} deleted")
    return True


async def delete_all_projects(db: AsyncSession, owner_id: uuid.UUID) -> int:
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.files))
        .filter(models.Project.owner_id == owner_id)
    )
    projects = result.scalars().all()
    count = 0
    for p in projects:
        await delete_project(db, p)
        count += 1
    logger.info(f"🗑 Deleted {count} projects for owner {owner_id}")
    return count


# Project Files CRUD
async def add_project_file(
    db: AsyncSession,
    project_id: uuid.UUID,
    upload_file: Union[dict, UploadFile],
) -> models.ProjectFile:

    if isinstance(upload_file, dict) and "file_path" in upload_file:
        db_file = models.ProjectFile(
            project_id=project_id,
            file_name=upload_file["file_name"],
            file_path=upload_file["file_path"],
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        logger.info(f"📎 Added existing file {db_file.file_name} to project {project_id}")
        return db_file

    # Upload user file to blob under projects/{project_id}/
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
    logger.info(f" Uploaded and attached file {upload_file.filename} -> {unique_name}")
    return db_file


async def add_project_files(
    db: AsyncSession,
    project_id: uuid.UUID,
    files: List[Union[dict, UploadFile]],
) -> List[models.ProjectFile]:
    results = []
    for f in files:
        results.append(await add_project_file(db, project_id, f))
    logger.info(f" Added {len(results)} files to project {project_id}")
    return results


async def list_project_files(db: AsyncSession, project_id: uuid.UUID) -> List[models.ProjectFile]:
    result = await db.execute(
        select(models.ProjectFile)
        .filter(models.ProjectFile.project_id == project_id)
        .order_by(models.ProjectFile.uploaded_at.desc())
    )
    files = result.scalars().all()
    logger.info(f" Listed {len(files)} files for project {project_id}")
    return files


# Finalized Scope Utilities

async def has_finalized_scope(db: AsyncSession, project_id: uuid.UUID) -> bool:
    """
    Check in DB if finalized_scope.json exists for a given project.
    """
    result = await db.execute(
        select(models.ProjectFile).filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json"
        )
    )
    return result.scalar_one_or_none() is not None


# Finalize Scope

async def finalize_scope(
    db: AsyncSession,
    project_id: uuid.UUID,
    scope_data: dict
) -> tuple[models.ProjectFile, dict]:
    from app.utils.export import normalize_scope

    logger.info(f" Finalizing scope for project {project_id}...")

    # Normalize scope data
    normalized = normalize_scope(scope_data)
    overview = normalized.get("overview", {})

    # Update Project table fields from overview
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.files))
        .filter(models.Project.id == project_id)
    )
    db_project = result.scalars().first()

    if db_project and overview:
        db_project.name = overview.get("Project Name") or db_project.name
        db_project.domain = overview.get("Domain") or db_project.domain
        db_project.complexity = overview.get("Complexity") or db_project.complexity
        db_project.tech_stack = overview.get("Tech Stack") or db_project.tech_stack
        db_project.use_cases = overview.get("Use Cases") or db_project.use_cases
        db_project.compliance = overview.get("Compliance") or db_project.compliance
        db_project.duration = str(overview.get("Duration") or db_project.duration)
        await db.commit()
        await db.refresh(db_project)
        logger.info(f"Updated project {project_id} metadata from finalized scope")

    # Remove old finalized scope if exists
    result = await db.execute(
        select(models.ProjectFile)
        .filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json"
        )
    )
    old_file = result.scalars().first()
    if old_file:
        try:
            await blob_utils.delete_blob(old_file.file_path)
            await db.delete(old_file)
            await db.commit()
            logger.info(f" Removed old finalized_scope.json for project {project_id}")
        except Exception as e:
            logger.warning(f" Failed to delete old finalized_scope.json from blob: {e}")

    # Upload new finalized_scope.json to blob
    blob_name = f"{PROJECTS_BASE}/{project_id}/finalized_scope.json"
    await blob_utils.upload_bytes(
        json.dumps(normalized, ensure_ascii=False, indent=2).encode("utf-8"),
        blob_name
    )
    logger.info(f" Uploaded new finalized_scope.json -> {blob_name}")

    db_file = models.ProjectFile(
        project_id=project_id,
        file_name="finalized_scope.json",
        file_path=blob_name,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    logger.info(f" Finalized scope stored for project {project_id}")
    return db_file, {**normalized, "_finalized": True}
