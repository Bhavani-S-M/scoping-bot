from __future__ import annotations
import uuid
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi_users import schemas as fa_schemas

# User
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

# Authentication
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Project File
class ProjectFile(BaseModel):
    id: uuid.UUID
    file_name: str
    file_path: str
    uploaded_at: datetime
    url: Optional[str] = None

    class Config:
        from_attributes = True


# Project
class ProjectBase(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    complexity: Optional[str] = None
    tech_stack: Optional[str] = None
    use_cases: Optional[str] = None
    compliance: Optional[str] = None
    duration: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: uuid.UUID
    files: List[ProjectFile] = []
    owner_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime]
    has_finalized_scope: bool = False

    class Config:
        from_attributes = True


# Scope Response
class GeneratedScopeResponse(BaseModel):
    overview: Optional[Dict[str, Any]] = {}
    activities: Optional[List[Dict[str, Any]]] = []
    resourcing_plan: Optional[List[Dict[str, Any]]] = []


# Generic Responses
class MessageResponse(BaseModel):
    msg: str
    scope: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None
    has_finalized_scope: Optional[bool] = None


class ProjectCreateResponse(BaseModel):
    project_id: uuid.UUID
    scope: Optional[GeneratedScopeResponse]
    redirect_url: Optional[str]
    has_finalized_scope: bool = False
