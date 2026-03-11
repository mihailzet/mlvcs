from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://mlvcs:mlvcs_secret@localhost:5432/mlvcs_db"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "ml-artifacts"
    MINIO_SECURE: bool = False
    SECRET_KEY: str = "supersecretkey"
    GIT_REPOS_PATH: str = "/app/git_repos"

    class Config:
        env_file = ".env"


settings = Settings()
