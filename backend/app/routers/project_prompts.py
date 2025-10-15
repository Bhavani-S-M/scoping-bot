from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.config.database import get_async_session
from app.models import Project, User
from app.auth import fastapi_users
from app.utils import project_prompts as prompt_utils
from app import schemas

current_active_user = fastapi_users.current_user(active=True)
router = APIRouter(prefix="/api/projects", tags=["Project Prompts"])


#GET — all prompts for a given project
@router.get("/{project_id}/prompts", response_model=schemas.PromptListResponse)
async def get_prompts(
    project_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    prompts = await prompt_utils.get_prompts_for_project(db, project_id)
    return {
        "prompts": [
            schemas.PromptRead(
                id=p.id,
                project_id=p.project_id,
                user_id=p.user_id,
                role=p.role,
                message=p.message,
                created_at=p.created_at,
            )
            for p in prompts
        ]
    }


# POST — add new prompt message
@router.post(
    "/{project_id}/prompts",
    response_model=schemas.PromptRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_prompt(
    project_id: UUID,
    payload: schemas.PromptCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    prompt = await prompt_utils.add_prompt_message(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        role=payload.role,
        message=payload.message,
    )

    return schemas.PromptRead.from_orm(prompt)


# PUT — update a prompt message
@router.put(
    "/{project_id}/prompts/{prompt_id}",
    response_model=schemas.PromptRead,
)
async def update_prompt(
    project_id: UUID,
    prompt_id: UUID,
    payload: schemas.PromptUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    prompts = await prompt_utils.get_prompts_for_project(db, project_id)
    prompt = next((p for p in prompts if str(p.id) == str(prompt_id)), None)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.message = payload.message.strip()
    await db.commit()
    await db.refresh(prompt)

    return schemas.PromptRead.from_orm(prompt)
# DELETE — clear all prompts for a project
@router.delete(
    "/{project_id}/prompts/clear",
    status_code=status.HTTP_200_OK,
)
async def clear_project_prompts(
    project_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await prompt_utils.clear_all_prompts(db, project_id)
    return {"status": "cleared"}


# DELETE — delete a specific prompt
@router.delete(
    "/{project_id}/prompts/{prompt_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_prompt(
    project_id: UUID,
    prompt_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
):
    prompt = await prompt_utils.delete_prompt(db, project_id, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return {"status": "deleted"}
