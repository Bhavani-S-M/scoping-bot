import uuid
import datetime
from sqlalchemy import (
    String, Text, DateTime, ForeignKey, Float, event
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from app.config.database import Base
from app.utils import azure_blob


# USER MODEL
class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(length=50), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    rate_cards: Mapped[list["RateCard"]] = relationship(
        "RateCard", back_populates="user", cascade="all, delete-orphan"
    )
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={str(self.id)[:8]}, username={self.username})>"


# COMPANY MODEL
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    owner: Mapped["User"] = relationship("User", back_populates="companies")

    # Relationships
    rate_cards: Mapped[list["RateCard"]] = relationship(
        "RateCard", back_populates="company", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="company"
    )

    def __repr__(self):
        return f"<Company(name={self.name}, owner={str(self.owner_id)[:8]}, currency={self.currency})>"

# RATE CARD MODEL
class RateCard(Base):
    __tablename__ = "rate_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    role_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    monthly_rate: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="rate_cards")
    user: Mapped["User"] = relationship("User", back_populates="rate_cards")

    def __repr__(self):
        who = f"user={self.user_id}" if self.user_id else "default"
        return f"<RateCard({who}, company={self.company_id}, role={self.role_name}, rate={self.monthly_rate})>"


# PROJECT MODEL
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # Core fields
    name: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    complexity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tech_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    use_cases: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Audit
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Owner
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    owner: Mapped["User"] = relationship("User", back_populates="projects")

    # Company association
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True
    )
    company: Mapped["Company"] = relationship("Company", back_populates="projects")

    # Related uploaded files
    files: Mapped[list["ProjectFile"]] = relationship(
        "ProjectFile", back_populates="project", cascade="all, delete-orphan"
    )

    prompt_history: Mapped[list["ProjectPromptHistory"]] = relationship(
        "ProjectPromptHistory",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(id={str(self.id)[:8]}, name={self.name[:25] if self.name else None})>"


# PROJECT FILE MODEL
class ProjectFile(Base):
    __tablename__ = "project_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    project: Mapped["Project"] = relationship("Project", back_populates="files")

    @property
    def url(self) -> str | None:
        """Return public blob URL for this file."""
        from app.utils.azure_blob import get_blob_url
        try:
            return get_blob_url(self.file_path)
        except Exception:
            return None

    def __repr__(self):
        return f"<ProjectFile(id={str(self.id)[:8]}, name={self.file_name})>"

# PROJECT PROMPT HISTORY MODEL
class ProjectPromptHistory(Base):
    __tablename__ = "project_prompt_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),  
        index=True,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),    
        index=True,
        nullable=True,
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)  
    message: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="prompt_history")
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<PromptHistory(role={self.role}, project={str(self.project_id)[:8]})>"


@event.listens_for(Project, "after_delete")
def delete_project_folder(mapper, connection, target):
    """Delete all blobs under the project's folder (safe + explicit)."""
    try:
        from app.utils import azure_blob
        prefix = f"projects/{target.id}/"

        # This ensures folder deletion only when a project is truly deleted
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(azure_blob.delete_folder(prefix))
        except RuntimeError:
            asyncio.run(azure_blob.delete_folder(prefix))

        # mark so individual files won’t be deleted again
        setattr(target, "_blob_folder_deleted", True)

    except Exception as e:
        print(f"[Project] Failed to cleanup folder {prefix}: {e}")


@event.listens_for(ProjectFile, "after_delete")
def delete_blob_after_file_delete(mapper, connection, target):
    """Delete single blob only if it’s not part of a project folder deletion."""
    try:
        # Skip if the parent project was just deleted
        if getattr(getattr(target, "project", None), "_blob_folder_deleted", False):
            return

        # Delete only files with extension (not folders)
        if target.file_path and "." in target.file_path:
            from app.utils import azure_blob
            azure_blob.safe_delete_blob(target.file_path)

    except Exception as e:
        print(f"[File] Failed to delete blob {getattr(target, 'file_path', None)}: {e}")
