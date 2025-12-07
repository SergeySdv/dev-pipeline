import os
import subprocess
from pathlib import Path

import pytest

from deksdenflow import project_setup


def _init_origin_repo(origin: Path) -> None:
    origin.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(origin)], check=True)
    (origin / "README.md").write_text("hello", encoding="utf-8")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "tester",
        "GIT_AUTHOR_EMAIL": "tester@example.com",
        "GIT_COMMITTER_NAME": "tester",
        "GIT_COMMITTER_EMAIL": "tester@example.com",
    }
    subprocess.run(["git", "-C", str(origin), "add", "README.md"], check=True, env=env)
    subprocess.run(["git", "-C", str(origin), "commit", "-m", "init"], check=True, env=env)


def test_ensure_local_repo_clones_when_missing(tmp_path) -> None:
    origin = tmp_path / "origin"
    _init_origin_repo(origin)
    projects_root = tmp_path / "Projects"
    git_url = origin.as_uri()

    repo_path = project_setup.ensure_local_repo(git_url, "demo", projects_root=projects_root, clone_if_missing=True)

    assert repo_path.exists()
    assert repo_path.parent == projects_root
    assert (repo_path / ".git").exists()
    assert repo_path.name == "origin"


def test_ensure_local_repo_respects_auto_clone_flag(tmp_path, monkeypatch) -> None:
    projects_root = tmp_path / "Projects"
    monkeypatch.setenv("DEKSDENFLOW_AUTO_CLONE", "false")
    with pytest.raises(FileNotFoundError):
        project_setup.ensure_local_repo("https://example.com/repo.git", "demo", projects_root=projects_root, clone_if_missing=None)
