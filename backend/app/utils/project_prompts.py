from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID
from app.models import ProjectPromptHistory
import logging

logger = logging.getLogger(__name__)


async def get_prompts_for_project(db: AsyncSession, project_id: UUID):
    """Fetch all prompts for a specific project, ordered by creation time."""
    result = await db.execute(
        select(ProjectPromptHistory)
        .where(ProjectPromptHistory.project_id == project_id)
        .order_by(ProjectPromptHistory.created_at.asc())
    )
    return result.scalars().all()


async def add_prompt_message(db: AsyncSession, project_id: UUID, user_id: UUID, role: str, message: str):
    """Insert a new prompt into history."""
    prompt = ProjectPromptHistory(
        project_id=project_id,
        user_id=user_id,
        role=role,
        message=message,
    )
    db.add(prompt)
    await db.flush()  # ensures the object gets an ID before commit
    await db.commit()
    await db.refresh(prompt)
    logger.info(f" Added new prompt ({role}) for project {project_id}")
    return prompt


async def delete_prompt(db: AsyncSession, project_id: UUID, prompt_id: UUID):
    """Delete a specific prompt by ID."""
    result = await db.execute(
        select(ProjectPromptHistory).where(
            ProjectPromptHistory.id == prompt_id,
            ProjectPromptHistory.project_id == project_id,
        )
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        return None

    await db.delete(prompt)
    await db.commit()
    logger.info(f"Deleted prompt {prompt_id} from project {project_id}")
    return prompt


async def clear_all_prompts(db: AsyncSession, project_id: UUID):
    """Delete all prompts for a given project."""
    await db.execute(
        delete(ProjectPromptHistory).where(ProjectPromptHistory.project_id == project_id)
    )
    await db.commit()
    logger.info(f"Cleared all prompts for project {project_id}")
    return True
