from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.database import get_db
from app.models import Experiment, Project
from app.schemas import ExperimentCreate, ExperimentUpdate, ExperimentResponse

router = APIRouter()


@router.post("/{project_id}/experiments", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(project_id: str, data: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    exp = Experiment(
        project_id=project_id,
        name=data.name,
        description=data.description,
        params=data.params,
        tags=data.tags,
        git_commit_hash=data.git_commit_hash,
        status="created",
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


@router.get("/{project_id}/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    project_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Experiment).where(Experiment.project_id == project_id)
    if status:
        query = query.where(Experiment.status == status)
    query = query.order_by(Experiment.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{project_id}/experiments/{exp_id}", response_model=ExperimentResponse)
async def get_experiment(project_id: str, exp_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Experiment).where(Experiment.id == exp_id, Experiment.project_id == project_id)
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.patch("/{project_id}/experiments/{exp_id}", response_model=ExperimentResponse)
async def update_experiment(project_id: str, exp_id: str, data: ExperimentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Experiment).where(Experiment.id == exp_id, Experiment.project_id == project_id)
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if data.status is not None:
        exp.status = data.status
    if data.metrics is not None:
        exp.metrics = data.metrics
    if data.params is not None:
        exp.params = data.params
    if data.tags is not None:
        exp.tags = data.tags

    await db.commit()
    await db.refresh(exp)
    return exp


@router.delete("/{project_id}/experiments/{exp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(project_id: str, exp_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Experiment).where(Experiment.id == exp_id, Experiment.project_id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Experiment not found")
    await db.execute(delete(Experiment).where(Experiment.id == exp_id))
    await db.commit()
