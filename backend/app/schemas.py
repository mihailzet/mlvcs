from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ── Project ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    git_repo_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Experiment ────────────────────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    git_commit_hash: Optional[str] = None


class ExperimentUpdate(BaseModel):
    status: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ExperimentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str]
    status: str
    params: Optional[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    git_commit_hash: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── ModelVersion ──────────────────────────────────────────────────────────────

class ModelVersionCreate(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=255)
    framework: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    git_commit_hash: Optional[str] = None


class ModelVersionResponse(BaseModel):
    id: str
    experiment_id: str
    version: str
    model_name: str
    framework: Optional[str]
    artifact_path: Optional[str]
    artifact_size: Optional[float]
    metrics: Optional[Dict[str, Any]]
    params: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    is_production: bool
    git_commit_hash: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── CodeCommit ────────────────────────────────────────────────────────────────

class CommitCreate(BaseModel):
    message: str
    author: Optional[str] = None
    branch: Optional[str] = "main"
    files: Optional[List[Dict[str, str]]] = None   # [{path: str, content: str}]


class CommitResponse(BaseModel):
    id: str
    project_id: str
    commit_hash: str
    message: str
    author: Optional[str]
    branch: Optional[str]
    files_changed: Optional[Any]
    diff_summary: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
