import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

# Make scripts/ importable
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import project_setup  # type: ignore  # noqa: E402


class ProjectSetupHarnessTest(unittest.TestCase):
    def test_project_setup_creates_all_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            cmd = [
                "python3",
                str(Path(__file__).resolve().parents[1] / "scripts" / "project_setup.py"),
                "--base-branch",
                "main",
                "--init-if-needed",
            ]
            subprocess.run(cmd, cwd=repo_dir, check=True, env=os.environ.copy())

            # Git repo initialized
            self.assertTrue((repo_dir / ".git").exists(), ".git should exist after setup")

            # All expected files from BASE_FILES exist
            for rel_path in project_setup.BASE_FILES:
                target = repo_dir / rel_path
                self.assertTrue(target.is_file(), f"Expected file not created: {target}")

            # CI scripts should be executable
            for name in ["bootstrap.sh", "lint.sh", "typecheck.sh", "test.sh", "build.sh"]:
                path = repo_dir / "scripts" / "ci" / name
                self.assertTrue(path.is_file(), f"Missing CI script: {path}")
                mode = path.stat().st_mode
                self.assertTrue(mode & stat.S_IXUSR, f"CI script not executable: {path}")

            # Workflows should exist
            self.assertTrue((repo_dir / ".github" / "workflows" / "ci.yml").is_file())
            self.assertTrue((repo_dir / ".gitlab-ci.yml").is_file())


if __name__ == "__main__":
    unittest.main()
