import os
import shutil
import subprocess
from pathlib import Path

from tasksgodzilla.domain import ProtocolStatus
from tasksgodzilla.services import OnboardingService
from tasksgodzilla.storage import Database


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)
    (path / "README.md").write_text("demo", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "tester",
        "GIT_AUTHOR_EMAIL": "tester@example.com",
        "GIT_COMMITTER_NAME": "tester",
        "GIT_COMMITTER_EMAIL": "tester@example.com",
    }
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, env=env)


def test_onboarding_service_emits_clarifications_without_block(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    monkeypatch.setenv("TASKSGODZILLA_AUTO_CLONE", "false")

    # Treat Codex/OpenCode CLIs as unavailable so discovery path logs a skip but does not fail.
    # Also set TASKSGODZILLA_DEFAULT_ENGINE_ID to codex to use the original codex path (which checks for codex CLI).
    import tasksgodzilla.services.onboarding as onboarding_mod

    _orig_which = shutil.which
    monkeypatch.setattr(
        onboarding_mod.shutil,
        "which",
        lambda name: None if name in ("codex", "opencode") else _orig_which(name),
    )
    # Ensure no API key is set so opencode engine falls back to CLI check
    monkeypatch.delenv("TASKSGODZILLA_OPENCODE_API_KEY", raising=False)


    db = Database(tmp_path / "db.sqlite")
    db.init_schema()
    project = db.create_project("demo", str(repo), "main", "github", {"planning": "zai-coding-plan/glm-4.6"})
    run = db.create_protocol_run(project.id, "setup-test", ProtocolStatus.PENDING, "main", None, None, "setup")

    service = OnboardingService(db=db)
    service.run_project_setup_job(project.id, protocol_run_id=run.id)

    run_after = db.get_protocol_run(run.id)
    assert run_after.status == ProtocolStatus.COMPLETED
    events = db.list_events(run.id)
    clar = [e for e in events if e.event_type == "setup_clarifications"]
    assert clar, "expected clarifications event"
    assert clar[0].metadata.get("blocking") is False


def test_onboarding_service_clarifications_can_block(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    monkeypatch.setenv("TASKSGODZILLA_AUTO_CLONE", "false")
    monkeypatch.setenv("TASKSGODZILLA_REQUIRE_ONBOARDING_CLARIFICATIONS", "true")


    import tasksgodzilla.services.onboarding as onboarding_mod

    _orig_which = shutil.which
    monkeypatch.setattr(
        onboarding_mod.shutil,
        "which",
        lambda name: None if name in ("codex", "opencode") else _orig_which(name),
    )
    # Ensure no API key is set so opencode engine falls back to CLI check
    monkeypatch.delenv("TASKSGODZILLA_OPENCODE_API_KEY", raising=False)


    db = Database(tmp_path / "db2.sqlite")
    db.init_schema()
    project = db.create_project("demo", str(repo), "main", "github", None)
    run = db.create_protocol_run(project.id, "setup-test2", ProtocolStatus.PENDING, "main", None, None, "setup")

    service = OnboardingService(db=db)
    service.run_project_setup_job(project.id, protocol_run_id=run.id)

    run_after = db.get_protocol_run(run.id)
    assert run_after.status == ProtocolStatus.BLOCKED
    events = db.list_events(run.id)
    blocked = [e for e in events if e.event_type == "setup_blocked"]
    assert blocked, "expected blocked event for clarifications"

