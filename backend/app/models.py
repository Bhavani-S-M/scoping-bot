import uuid
import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from app.config.database import Base


# User
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

    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={str(self.id)[:8]}, username={self.username})>"


#  Project
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # Core fields
    name: Mapped[str | None] = mapped_column(String, index=True, nullable=True)    
    domain: Mapped[str | None] = mapped_column(String, nullable=True)              
    complexity: Mapped[str | None] = mapped_column(String, nullable=True)
    tech_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    use_cases: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[str | None] = mapped_column(String, nullable=True)

    # Audit
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Owner
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    owner: Mapped["User"] = relationship("User", back_populates="projects")

    # Related uploaded files
    files: Mapped[list["ProjectFile"]] = relationship(
        "ProjectFile", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(id={str(self.id)[:8]}, name={self.name[:20]})>"

# ProjectFile
class ProjectFile(Base):
    __tablename__ = "project_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
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

