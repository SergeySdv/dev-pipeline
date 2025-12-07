import subprocess
import sys
from pathlib import Path


def test_offline_check_passes_when_files_present(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    for rel in [
        "prompts/repo-discovery.prompt.md",
        "docs/solution-design.md",
        "docs/implementation-plan.md",
        "docs/tasksgodzilla.md",
        "docs/terraformmanager-workflow-plan.md",
    ]:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "offline_discovery_check.py"
    proc = subprocess.run([sys.executable, str(script), "--repo-root", str(repo), "--strict"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "passed" in proc.stdout.lower()


def test_offline_check_flags_missing_files(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve().parents[1] / "scripts" / "offline_discovery_check.py"
    proc = subprocess.run([sys.executable, str(script), "--repo-root", str(repo), "--strict"], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "missing" in proc.stdout.lower()
