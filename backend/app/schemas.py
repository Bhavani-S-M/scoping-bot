from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from fastapi_users import schemas as fa_schemas


# USER SCHEMAS
class UserRead(fa_schemas.BaseUser[uuid.UUID]):
    username: str
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]


class UserCreate(fa_schemas.BaseUserCreate):
    username: str


class UserUpdate(fa_schemas.BaseUserUpdate):
    username: Optional[str] = None


class UserList(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool

    class Config:
        from_attributes = True


# AUTHENTICATION
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# COMPANY + RATE CARD SCHEMAS
class CompanyBase(BaseModel):
    name: str
    currency: Optional[str] = "USD"


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class RateCardBase(BaseModel):
    role_name: str
    monthly_rate: float


class RateCardCreate(RateCardBase):
    pass


class RateCardUpdate(BaseModel):
    monthly_rate: float


class RateCardRead(RateCardBase):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


# PROJECT FILE SCHEMAS
class ProjectFile(BaseModel):
    id: uuid.UUID
    file_name: str
    file_path: str
    uploaded_at: datetime
    download_url: Optional[str] = None
    preview_url: Optional[str] = None

    class Config:
        from_attributes = True


#  PROJECT SCHEMAS
class ProjectBase(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    complexity: Optional[str] = None
    tech_stack: Optional[str] = None
    use_cases: Optional[str] = None
    compliance: Optional[str] = None
    duration: Optional[str] = None


class ProjectCreate(ProjectBase):
    company_id: Optional[uuid.UUID] = None


class Project(ProjectBase):
    id: uuid.UUID
    files: List[ProjectFile] = []
    owner_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    company: Optional[CompanyRead] = None
    created_at: datetime
    updated_at: Optional[datetime]
    has_finalized_scope: bool = False

    class Config:
        from_attributes = True


# SCOPE & GENERATION SCHEMAS
class GeneratedScopeResponse(BaseModel):
    overview: Dict[str, Any] = {}
    activities: List[Dict[str, Any]] = []
    resourcing_plan: List[Dict[str, Any]] = []
    architecture_diagram: Optional[str] = None
    discount_percentage: Optional[float] = None  # Add discount support
    _finalized: Optional[bool] = None


class MessageResponse(BaseModel):
    msg: str
    scope: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None
    has_finalized_scope: Optional[bool] = None
    architecture_diagram: Optional[str] = None


class RegenerateScopeRequest(BaseModel):
    draft: Dict[str, Any]
    instructions: str


#  QUESTION GENERATION SCHEMAS
class QuestionItem(BaseModel):
    question: str
    user_understanding: Optional[str] = ""
    comment: Optional[str] = ""


class QuestionCategory(BaseModel):
    category: str
    items: List[QuestionItem]


class GenerateQuestionsResponse(BaseModel):
    msg: str
    questions: List[QuestionCategory]


#  PROMPT HISTORY SCHEMAS
class RoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class PromptBase(BaseModel):
    role: RoleEnum = Field(default=RoleEnum.user, description="Role of the speaker")
    message: str = Field(..., min_length=1, description="Prompt text content")


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    message: str = Field(..., min_length=1)


class PromptRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    role: RoleEnum
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class PromptListResponse(BaseModel):
    prompts: List[PromptRead]

    class Config:
        from_attributes = True


class StatusResponse(BaseModel):
    status: str
