from typing import List, Optional, Union
from sqlalchemy.orm import Session, joinedload
import uuid, logging, json
from fastapi import UploadFile
from app import models, schemas
from app.utils import azure_blob as blob_utils

logger = logging.getLogger(__name__)

# Constants
PROJECTS_BASE = "projects"


# Projects CRUD

def list_projects(db: Session, owner_id: uuid.UUID) -> List[models.Project]:
    return (
        db.query(models.Project)
        .options(joinedload(models.Project.files))
        .filter(models.Project.owner_id == owner_id)
        .order_by(models.Project.created_at.desc())
        .all()
    )


def get_project(db: Session, project_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[models.Project]:
    return (
        db.query(models.Project)
        .options(joinedload(models.Project.files))
        .filter(models.Project.id == project_id, models.Project.owner_id == owner_id)
        .first()
    )


def create_project(
    db: Session,
    project: schemas.ProjectCreate,
    owner_id: uuid.UUID,
    files: list[UploadFile] | None = None
) -> models.Project:
    db_project = models.Project(**project.dict(), owner_id=owner_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    if files:
        add_project_files(db, db_project.id, files)
    return db_project


def update_project(db: Session, db_project: models.Project, update_data: schemas.ProjectBase) -> models.Project:
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(db_project, field, value)
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, db_project: models.Project) -> bool:
    for f in db_project.files:
        try:
            if f.file_path:
                blob_utils.delete_blob(f.file_path)
                logger.info(f"🗑 Deleted blob: {f.file_path}")
        except Exception as e:
            logger.warning(f" Failed to delete blob {f.file_path}: {e}")

    db.delete(db_project)
    db.commit()
    return True


def delete_all_projects(db: Session, owner_id: uuid.UUID) -> int:
    projects = (
        db.query(models.Project)
        .options(joinedload(models.Project.files))
        .filter(models.Project.owner_id == owner_id)
        .all()
    )
    count = 0
    for p in projects:
        delete_project(db, p)
        count += 1
    return count


# Project Files CRUD

def add_project_file(
    db: Session,
    project_id: uuid.UUID,
    upload_file: Union[dict, UploadFile],
) -> models.ProjectFile:

    if isinstance(upload_file, dict) and "file_path" in upload_file:
        # Directly reference an existing blob
        db_file = models.ProjectFile(
            project_id=project_id,
            file_name=upload_file["file_name"],
            file_path=upload_file["file_path"],  # blob path already prefixed
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file

    # Upload user file to blob under projects/{project_id}/
    safe_name = upload_file.filename.replace(" ", "_")
    unique_name = f"{PROJECTS_BASE}/{project_id}/{uuid.uuid4()}_{safe_name}"
    blob_utils.upload_bytes(upload_file.file.read(), unique_name)

    db_file = models.ProjectFile(
        project_id=project_id,
        file_name=upload_file.filename,
        file_path=unique_name,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


def add_project_files(
    db: Session,
    project_id: uuid.UUID,
    files: List[Union[dict, UploadFile]],
) -> List[models.ProjectFile]:
    return [add_project_file(db, project_id, f) for f in files]


def list_project_files(db: Session, project_id: uuid.UUID) -> List[models.ProjectFile]:
    return (
        db.query(models.ProjectFile)
        .filter(models.ProjectFile.project_id == project_id)
        .order_by(models.ProjectFile.uploaded_at.desc())
        .all()
    )


# Finalize Scope

def finalize_scope(
    db: Session,
    project_id: uuid.UUID,
    scope_data: dict
) -> tuple[models.ProjectFile, dict]:
    from app.utils.export import normalize_scope

    # Normalize scope data
    normalized = normalize_scope(scope_data)
    overview = normalized.get("overview", {})

    # Update Project table fields from overview
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project and overview:
        db_project.name = overview.get("Project Name") or db_project.name
        db_project.domain = overview.get("Domain") or db_project.domain
        db_project.complexity = overview.get("Complexity") or db_project.complexity
        db_project.tech_stack = overview.get("Tech Stack") or db_project.tech_stack
        db_project.use_cases = overview.get("Use Cases") or db_project.use_cases
        db_project.compliance = overview.get("Compliance") or db_project.compliance
        db_project.duration = str(overview.get("Duration") or db_project.duration)
        db.commit()
        db.refresh(db_project)

    # Remove old finalized scope in blob if exists 
    old_file = (
        db.query(models.ProjectFile)
        .filter(
            models.ProjectFile.project_id == project_id,
            models.ProjectFile.file_name == "finalized_scope.json"
        )
        .first()
    )
    if old_file:
        try:
            blob_utils.delete_blob(old_file.file_path)  # ✅ no base param
            db.delete(old_file)
            db.commit()
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete old finalized_scope.json from blob: {e}")

    # Upload new finalized_scope.json to blob
    blob_name = f"{PROJECTS_BASE}/{project_id}/finalized_scope.json"
    blob_utils.upload_bytes(
        json.dumps(normalized, ensure_ascii=False, indent=2).encode("utf-8"),
        blob_name
    )

    db_file = models.ProjectFile(
        project_id=project_id,
        file_name="finalized_scope.json",
        file_path=blob_name, 
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return db_file, normalized
