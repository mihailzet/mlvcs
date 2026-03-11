from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.routers import projects, experiments, models, commits
from app.services.minio_service import init_minio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_minio()
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="ML Versioning Control System",
    description="Система управления версиями кода и состояний ML-моделей",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(experiments.router, prefix="/api/v1/projects", tags=["Experiments"])
app.include_router(models.router, prefix="/api/v1/experiments", tags=["Models"])
app.include_router(commits.router, prefix="/api/v1/projects", tags=["Commits"])


@app.get("/")
async def root():
    return {"message": "ML Versioning Control System", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
