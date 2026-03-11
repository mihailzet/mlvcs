from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Float, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    git_repo_path = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    experiments = relationship("Experiment", back_populates="project", cascade="all, delete-orphan")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="created")  # created, running, completed, failed
    params = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    git_commit_hash = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="experiments")
    model_versions = relationship("ModelVersion", back_populates="experiment", cascade="all, delete-orphan")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True, default=gen_uuid)
    experiment_id = Column(String, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)
    model_name = Column(String(255), nullable=False, index=True)
    framework = Column(String(100), nullable=True)   # pytorch, tensorflow, sklearn, etc
    artifact_path = Column(String(512), nullable=True)  # path in MinIO
    artifact_size = Column(Float, nullable=True)        # bytes
    metrics = Column(JSON, nullable=True)
    params = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    is_production = Column(Boolean, default=False)
    git_commit_hash = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="model_versions")


class CodeCommit(Base):
    __tablename__ = "code_commits"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    commit_hash = Column(String(40), nullable=False, index=True)
    message = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    branch = Column(String(255), nullable=True)
    files_changed = Column(JSON, nullable=True)
    diff_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
