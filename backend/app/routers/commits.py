from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models import CodeCommit, Project
from app.schemas import CommitCreate, CommitResponse
from app.services import git_service

router = APIRouter()


@router.post("/{project_id}/commits", response_model=CommitResponse, status_code=status.HTTP_201_CREATED)
async def create_commit(project_id: str, data: CommitCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    files = data.files or []
    commit_info = git_service.commit_files(
        project_name=project.name,
        message=data.message,
        files=files,
        author=data.author or "MLVCS User",
        branch=data.branch or "main",
    )

    if "error" in commit_info:
        raise HTTPException(status_code=400, detail=commit_info["error"])

    record = CodeCommit(
        project_id=project_id,
        commit_hash=commit_info["commit_hash"],
        message=data.message,
        author=data.author,
        branch=data.branch,
        files_changed=commit_info.get("files_changed"),
        diff_summary=commit_info.get("diff_summary"),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{project_id}/commits", response_model=List[CommitResponse])
async def list_commits(
    project_id: str,
    branch: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(CodeCommit).where(CodeCommit.project_id == project_id)
    if branch:
        query = query.where(CodeCommit.branch == branch)
    query = query.order_by(CodeCommit.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{project_id}/commits/{commit_hash}/diff")
async def get_commit_diff(project_id: str, commit_hash: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    diff = git_service.get_diff(project.name, commit_hash)
    return {"commit_hash": commit_hash, "diff": diff}


@router.get("/{project_id}/history")
async def get_git_history(project_id: str, branch: Optional[str] = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    history = git_service.get_commit_history(project.name, branch=branch, limit=limit)
    return {"project": project.name, "commits": history}


@router.get("/{project_id}/branches")
async def get_branches(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    branches = git_service.list_branches(project.name)
    return {"project": project.name, "branches": branches}


@router.get("/{project_id}/file")
async def get_file_at_commit(
    project_id: str,
    file_path: str,
    commit_hash: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = git_service.get_file_content(project.name, file_path, commit_hash)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    return {"file_path": file_path, "commit_hash": commit_hash, "content": content}
