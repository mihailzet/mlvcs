import os
import git
from pathlib import Path
from typing import List, Dict, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def _repo_path(project_name: str) -> Path:
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
    return Path(settings.GIT_REPOS_PATH) / safe_name


def init_repo(project_name: str) -> str:
    path = _repo_path(project_name)
    path.mkdir(parents=True, exist_ok=True)

    if (path / ".git").exists():
        repo = git.Repo(path)
        logger.info(f"Opened existing repo at {path}")
    else:
        repo = git.Repo.init(path)
        # Create initial README commit
        readme = path / "README.md"
        readme.write_text(f"# {project_name}\n\nML project managed by MLVCS\n")
        repo.index.add(["README.md"])
        repo.index.commit(
            "Initial commit",
            author=git.Actor("MLVCS System", "mlvcs@system.local"),
            committer=git.Actor("MLVCS System", "mlvcs@system.local"),
        )
        logger.info(f"Initialized new repo at {path}")

    return str(path)


def commit_files(
    project_name: str,
    message: str,
    files: List[Dict[str, str]],
    author: str = "MLVCS User",
    branch: str = "main",
) -> Dict:
    path = _repo_path(project_name)

    if not (path / ".git").exists():
        init_repo(project_name)

    repo = git.Repo(path)

    # Ensure branch exists
    if branch != repo.active_branch.name:
        try:
            repo.git.checkout("-b", branch)
        except git.GitCommandError:
            repo.git.checkout(branch)

    # Write files
    changed = []
    for f in files:
        file_path = path / f["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f.get("content", ""))
        changed.append(f["path"])

    if not changed:
        return {"error": "No files to commit"}

    repo.index.add(changed)

    # Generate diff summary before commit
    try:
        diff_summary = repo.git.diff("HEAD", "--stat") if repo.head.is_valid() else "Initial commit"
    except Exception:
        diff_summary = "New files added"

    actor = git.Actor(author, f"{author.lower().replace(' ', '.')}@mlvcs.local")
    commit = repo.index.commit(
        message,
        author=actor,
        committer=git.Actor("MLVCS System", "mlvcs@system.local"),
    )

    return {
        "commit_hash": commit.hexsha,
        "message": message,
        "author": author,
        "branch": branch,
        "files_changed": changed,
        "diff_summary": diff_summary,
    }


def get_commit_history(project_name: str, branch: str = None, limit: int = 50) -> List[Dict]:
    path = _repo_path(project_name)
    if not (path / ".git").exists():
        return []

    repo = git.Repo(path)
    commits = []

    try:
        rev = branch if branch else repo.active_branch.name
        for commit in repo.iter_commits(rev, max_count=limit):
            commits.append({
                "hash": commit.hexsha,
                "short_hash": commit.hexsha[:7],
                "message": commit.message.strip(),
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "files": list(commit.stats.files.keys()),
            })
    except Exception as e:
        logger.error(f"Error getting commit history: {e}")

    return commits


def get_file_content(project_name: str, file_path: str, commit_hash: Optional[str] = None) -> Optional[str]:
    path = _repo_path(project_name)
    if not (path / ".git").exists():
        return None

    repo = git.Repo(path)

    try:
        if commit_hash:
            commit = repo.commit(commit_hash)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode("utf-8", errors="replace")
        else:
            full_path = path / file_path
            if full_path.exists():
                return full_path.read_text(errors="replace")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")

    return None


def get_diff(project_name: str, commit_hash: str, parent_hash: Optional[str] = None) -> str:
    path = _repo_path(project_name)
    if not (path / ".git").exists():
        return ""

    repo = git.Repo(path)
    try:
        commit = repo.commit(commit_hash)
        if parent_hash:
            parent = repo.commit(parent_hash)
            diff = repo.git.diff(parent.hexsha, commit.hexsha)
        else:
            if commit.parents:
                diff = repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
            else:
                diff = repo.git.show(commit.hexsha)
        return diff
    except Exception as e:
        logger.error(f"Error getting diff: {e}")
        return ""


def list_branches(project_name: str) -> List[str]:
    path = _repo_path(project_name)
    if not (path / ".git").exists():
        return []
    repo = git.Repo(path)
    return [b.name for b in repo.branches]
