import subprocess
import sys
from pathlib import Path


def test_checklist_skips_when_repo_missing(tmp_path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "terraformmanager_checklist.py"
    proc = subprocess.run([sys.executable, str(script), "--repo-root", str(tmp_path / "missing")], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "skipping" in proc.stdout.lower()


def test_checklist_passes_with_minimum_assets(tmp_path) -> None:
    repo = tmp_path / "tfm"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "service_manager.py").write_text("", encoding="utf-8")
    (repo / "frontend").mkdir(parents=True, exist_ok=True)
    (repo / "sample").mkdir(parents=True, exist_ok=True)
    (repo / "payloads").mkdir(parents=True, exist_ok=True)
    (repo / "backend" / "cli").mkdir(parents=True, exist_ok=True)
    (repo / "backend" / "cli" / "__init__.py").write_text("", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "terraformmanager_checklist.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(repo), "--strict"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "validated" in proc.stdout.lower()


def test_checklist_smoke_uses_commands_when_present(tmp_path) -> None:
    repo = tmp_path / "tfm"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    # Script returns zero to simulate a healthy help command.
    (repo / "scripts" / "service_manager.py").write_text("import sys\nprint('ok')\n", encoding="utf-8")
    (repo / "frontend").mkdir(parents=True, exist_ok=True)
    (repo / "sample").mkdir(parents=True, exist_ok=True)
    (repo / "payloads").mkdir(parents=True, exist_ok=True)
    (repo / "backend").mkdir(parents=True, exist_ok=True)
    (repo / "backend" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "backend" / "cli.py").write_text("def main():\n    return 0\nif __name__ == '__main__':\n    main()\n", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "terraformmanager_checklist.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(repo), "--strict", "--smoke"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "validated" in proc.stdout.lower()
