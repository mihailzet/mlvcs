from minio import Minio
from minio.error import S3Error
from app.config import settings
import io
import logging

logger = logging.getLogger(__name__)

_client: Minio = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


async def init_minio():
    client = get_minio_client()
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
            logger.info(f"Created MinIO bucket: {settings.MINIO_BUCKET}")
        else:
            logger.info(f"MinIO bucket already exists: {settings.MINIO_BUCKET}")
    except S3Error as e:
        logger.error(f"MinIO init error: {e}")
        raise


async def upload_artifact(object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = get_minio_client()
    data_stream = io.BytesIO(data)
    client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        data_stream,
        length=len(data),
        content_type=content_type,
    )
    return object_name


async def download_artifact(object_name: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(settings.MINIO_BUCKET, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def delete_artifact(object_name: str):
    client = get_minio_client()
    client.remove_object(settings.MINIO_BUCKET, object_name)


async def get_presigned_url(object_name: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta
    client = get_minio_client()
    url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )
    return url
