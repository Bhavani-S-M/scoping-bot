from __future__ import annotations
import uuid
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi_users import schemas as fa_schemas


# ==========================================================
# 👤 USER SCHEMAS
# ==========================================================
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


# ==========================================================
# 🔑 AUTHENTICATION
# ==========================================================
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ==========================================================
# 💰 COMPANY + RATE CARD SCHEMAS
# ==========================================================
class CompanyBase(BaseModel):
    name: str
    currency: Optional[str] = "USD"


class CompanyCreate(CompanyBase):
    """Used when creating a new company."""
    pass


class CompanyRead(CompanyBase):
    """Returned when reading company info."""
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None  # 👈 user who owns the company, None = global

    class Config:
        from_attributes = True


class RateCardBase(BaseModel):
    role_name: str
    monthly_rate: float


class RateCardCreate(RateCardBase):
    """Used when adding a new rate card."""
    pass


class RateCardUpdate(BaseModel):
    """Used when updating existing rate cards."""
    monthly_rate: float


class RateCardRead(RateCardBase):
    """Returned when fetching rate cards."""
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


# PROJECT SCHEMAS
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


# SCOPE RESPONSE
class GeneratedScopeResponse(BaseModel):
    overview: Dict[str, Any] = {}
    activities: List[Dict[str, Any]] = []
    resourcing_plan: List[Dict[str, Any]] = []
    architecture_diagram: Optional[str] = None


# GENERIC RESPONSES
class MessageResponse(BaseModel):
    msg: str
    scope: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None
    has_finalized_scope: Optional[bool] = None


# REGENERATE SCOPE
class RegenerateScopeRequest(BaseModel):
    draft: Dict[str, Any]
    instructions: str
# QUESTION GENERATION SCHEMAS
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
