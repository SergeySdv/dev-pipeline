import subprocess
from pathlib import Path

from devgodzilla.config import get_config
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.git import GitService


def _service() -> GitService:
    return GitService(ServiceContext(config=get_config()))


def test_push_and_open_pr_falls_back_to_host_git_credentials(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[list[str], dict | None]] = []

    def fake_run_process(cmd, *, cwd=None, check=True, env=None, **kwargs):
        calls.append((cmd, env))
        if cmd[:4] == ["git", "config", "--get", "remote.origin.url"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo.git\n", stderr="")
        if cmd[:2] == ["git", "add"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="[branch] commit\n", stderr="")
        if cmd[:4] == ["git", "push", "--set-upstream", "origin"]:
            if env is not None:
                raise subprocess.CalledProcessError(128, cmd, "", "remote: invalid token")
            return subprocess.CompletedProcess(cmd, 0, stdout="pushed\n", stderr="")
        if cmd[:4] == ["git", "ls-remote", "--exit-code", "--heads"]:
            return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="")
        if cmd[:3] == ["gh", "pr", "create"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo/pull/1\n", stderr="")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr("devgodzilla.services.git.run_process", fake_run_process)
    monkeypatch.setattr("devgodzilla.services.git.shutil.which", lambda tool: "/usr/bin/gh" if tool == "gh" else None)

    service = _service()
    assert service.push_and_open_pr(tmp_path, "feature/test", "main", github_token="stale-token") is True

    push_calls = [call for call in calls if call[0][:4] == ["git", "push", "--set-upstream", "origin"]]
    assert len(push_calls) == 2
    assert push_calls[0][1] is not None
    assert push_calls[1][1] is None


def test_push_and_open_pr_uses_current_worktree_branch(monkeypatch, tmp_path: Path) -> None:
    pushed_branch: list[str] = []

    def fake_run_process(cmd, *, cwd=None, check=True, env=None, **kwargs):
        if cmd[:4] == ["git", "config", "--get", "remote.origin.url"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo.git\n", stderr="")
        if cmd[:3] == ["git", "branch", "--show-current"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="028-feature-test\n", stderr="")
        if cmd[:2] == ["git", "add"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="[branch] commit\n", stderr="")
        if cmd[:4] == ["git", "push", "--set-upstream", "origin"]:
            pushed_branch.append(cmd[4])
            return subprocess.CompletedProcess(cmd, 0, stdout="pushed\n", stderr="")
        if cmd[:3] == ["gh", "pr", "create"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo/pull/3\n", stderr="")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr("devgodzilla.services.git.run_process", fake_run_process)
    monkeypatch.setattr("devgodzilla.services.git.shutil.which", lambda tool: "/usr/bin/gh" if tool == "gh" else None)

    service = _service()
    assert service.push_and_open_pr(tmp_path, "feature/test", "main", github_token=None) is True
    assert pushed_branch == ["028-feature-test"]


def test_open_pr_falls_back_to_host_cli_auth_when_project_token_fails(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[list[str], dict | None]] = []

    def fake_run_process(cmd, *, cwd=None, check=True, env=None, **kwargs):
        calls.append((cmd, env))
        if cmd[:4] == ["git", "config", "--get", "remote.origin.url"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo.git\n", stderr="")
        if cmd[:3] == ["gh", "pr", "create"]:
            if env is not None:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="authentication failed")
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo/pull/2\n", stderr="")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr("devgodzilla.services.git.run_process", fake_run_process)
    monkeypatch.setattr("devgodzilla.services.git.shutil.which", lambda tool: "/usr/bin/gh" if tool == "gh" else None)

    service = _service()
    result = service.open_pr(tmp_path, "feature/test", "main", github_token="stale-token")

    assert result["success"] is True
    assert result["url"] == "https://github.com/example/demo/pull/2"

    gh_calls = [call for call in calls if call[0][:3] == ["gh", "pr", "create"]]
    assert len(gh_calls) == 2
    assert gh_calls[0][1] is not None
    assert gh_calls[1][1] is None


def test_open_pr_treats_existing_cli_pr_as_success(monkeypatch, tmp_path: Path) -> None:
    def fake_run_process(cmd, *, cwd=None, check=True, env=None, **kwargs):
        if cmd[:4] == ["git", "config", "--get", "remote.origin.url"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo.git\n", stderr="")
        if cmd[:3] == ["gh", "pr", "create"]:
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr=(
                    'a pull request for branch "feature/test" into branch "main" already exists:\n'
                    "https://github.com/example/demo/pull/9\n"
                ),
            )
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr("devgodzilla.services.git.run_process", fake_run_process)
    monkeypatch.setattr("devgodzilla.services.git.shutil.which", lambda tool: "/usr/bin/gh" if tool == "gh" else None)

    service = _service()
    result = service.open_pr(tmp_path, "feature/test", "main")

    assert result["success"] is True
    assert result["url"] == "https://github.com/example/demo/pull/9"


def test_push_and_open_pr_stages_only_requested_changed_files(monkeypatch, tmp_path: Path) -> None:
    add_calls: list[list[str]] = []

    def fake_run_process(cmd, *, cwd=None, check=True, env=None, **kwargs):
        if cmd[:4] == ["git", "config", "--get", "remote.origin.url"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo.git\n", stderr="")
        if cmd[:3] == ["git", "branch", "--show-current"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="feature/storage-cleanup\n", stderr="")
        if cmd[:3] == ["git", "add", "-A"]:
            add_calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:4] == ["git", "diff", "--cached", "--name-only"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="README.md\nsrc/telegram_bot_app/telegram_bot.py\n",
                stderr="",
            )
        if cmd[:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="[branch] commit\n", stderr="")
        if cmd[:4] == ["git", "push", "--set-upstream", "origin"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="pushed\n", stderr="")
        if cmd[:3] == ["gh", "pr", "create"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/example/demo/pull/11\n", stderr="")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr("devgodzilla.services.git.run_process", fake_run_process)
    monkeypatch.setattr("devgodzilla.services.git.shutil.which", lambda tool: "/usr/bin/gh" if tool == "gh" else None)

    service = _service()
    assert (
        service.push_and_open_pr(
            tmp_path,
            "feature/test",
            "main",
            changed_files=["README.md", "src/telegram_bot_app/telegram_bot.py"],
        )
        is True
    )

    assert add_calls == [["git", "add", "-A", "--", "README.md", "src/telegram_bot_app/telegram_bot.py"]]
