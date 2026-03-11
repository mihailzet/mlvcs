from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
import io

from app.database import get_db
from app.models import ModelVersion, Experiment
from app.schemas import ModelVersionCreate, ModelVersionResponse
from app.services.minio_service import upload_artifact, download_artifact, get_presigned_url

router = APIRouter()


@router.post("/{experiment_id}/models", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_model_version(experiment_id: str, data: ModelVersionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Experiment not found")

    mv = ModelVersion(
        experiment_id=experiment_id,
        version=data.version,
        model_name=data.model_name,
        framework=data.framework,
        metrics=data.metrics,
        params=data.params,
        tags=data.tags,
        git_commit_hash=data.git_commit_hash,
    )
    db.add(mv)
    await db.commit()
    await db.refresh(mv)
    return mv


@router.post("/{experiment_id}/models/{model_id}/upload")
async def upload_model_artifact(
    experiment_id: str,
    model_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.id == model_id, ModelVersion.experiment_id == experiment_id)
    )
    mv = result.scalar_one_or_none()
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")

    content = await file.read()
    object_name = f"models/{experiment_id}/{model_id}/{file.filename}"
    await upload_artifact(object_name, content, file.content_type or "application/octet-stream")

    mv.artifact_path = object_name
    mv.artifact_size = len(content)
    await db.commit()
    await db.refresh(mv)

    return {"message": "Artifact uploaded", "path": object_name, "size_bytes": len(content)}


@router.get("/{experiment_id}/models/{model_id}/download")
async def download_model_artifact(experiment_id: str, model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.id == model_id, ModelVersion.experiment_id == experiment_id)
    )
    mv = result.scalar_one_or_none()
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")
    if not mv.artifact_path:
        raise HTTPException(status_code=404, detail="No artifact uploaded for this model version")

    data = await download_artifact(mv.artifact_path)
    filename = mv.artifact_path.split("/")[-1]

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{experiment_id}/models/{model_id}/url")
async def get_model_url(experiment_id: str, model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.id == model_id, ModelVersion.experiment_id == experiment_id)
    )
    mv = result.scalar_one_or_none()
    if not mv or not mv.artifact_path:
        raise HTTPException(status_code=404, detail="Artifact not found")

    url = await get_presigned_url(mv.artifact_path)
    return {"url": url, "expires_in": 3600}


@router.get("/{experiment_id}/models", response_model=List[ModelVersionResponse])
async def list_model_versions(experiment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.experiment_id == experiment_id).order_by(ModelVersion.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{experiment_id}/models/{model_id}/promote")
async def promote_to_production(experiment_id: str, model_id: str, db: AsyncSession = Depends(get_db)):
    # Demote all others first
    all_result = await db.execute(
        select(ModelVersion).where(ModelVersion.experiment_id == experiment_id)
    )
    for mv in all_result.scalars().all():
        mv.is_production = False

    result = await db.execute(
        select(ModelVersion).where(ModelVersion.id == model_id, ModelVersion.experiment_id == experiment_id)
    )
    mv = result.scalar_one_or_none()
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")

    mv.is_production = True
    await db.commit()
    return {"message": f"Model {mv.model_name} v{mv.version} promoted to production"}


@router.delete("/{experiment_id}/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_version(experiment_id: str, model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.id == model_id, ModelVersion.experiment_id == experiment_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Model version not found")
    await db.execute(delete(ModelVersion).where(ModelVersion.id == model_id))
    await db.commit()
