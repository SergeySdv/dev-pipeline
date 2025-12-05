import os
import shutil
import subprocess
import time
import unittest
from pathlib import Path

# Ensure scripts/ is importable to reach protocol_pipeline helpers
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import protocol_pipeline  # type: ignore  # noqa: E402


@unittest.skipUnless(
    os.getenv("RUN_REAL_CODEX") == "1",
    "Set RUN_REAL_CODEX=1 to run real Codex integration against README workflow.",
)
class ReadmeWorkflowIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("codex") is None:
            self.skipTest("codex CLI not found in PATH")

        self.repo_root = Path(__file__).resolve().parents[1]
        self.worktrees_root = self.repo_root.parent / "worktrees"

        short_name = f"readme-e2e-{int(time.time())}"
        self.protocol_number = protocol_pipeline.next_protocol_number(self.repo_root)
        self.protocol_name = f"{self.protocol_number}-{protocol_pipeline.slugify(short_name)}"
        self.worktree_path = self.worktrees_root / self.protocol_name

    def tearDown(self) -> None:
        # Remove worktree and branch if they were created. Ignore failures so cleanup is best-effort.
        subprocess.run(
            ["git", "worktree", "remove", "-f", str(self.worktree_path)],
            cwd=self.repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "branch", "-D", self.protocol_name],
            cwd=self.repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        # If anything remains, delete the directory to avoid residue.
        if self.worktree_path.exists():
            shutil.rmtree(self.worktree_path, ignore_errors=True)

    def test_protocol_pipeline_creates_worktree_and_plan(self) -> None:
        env = os.environ.copy()
        env.setdefault("PROTOCOL_PLANNING_MODEL", "gpt-5.1-codex-max")
        env.setdefault("PROTOCOL_DECOMPOSE_MODEL", "gpt-5.1-codex-max")
        env.setdefault("PROTOCOL_EXEC_MODEL", "gpt-5.1-codex-max")

        cmd = [
            "python3",
            "scripts/protocol_pipeline.py",
            "--base-branch",
            "main",
            "--short-name",
            self.protocol_name.split("-", 1)[1],
            "--description",
            "README workflow integration test",
        ]

        proc = subprocess.run(
            cmd,
            cwd=self.repo_root,
            env=env,
            input="y\n",
            text=True,
            capture_output=True,
            timeout=900,
        )

        if proc.returncode != 0:
            self.fail(
                f"protocol_pipeline failed (rc={proc.returncode}):\nstdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"
            )

        protocol_root = self.worktree_path / ".protocols" / self.protocol_name
        plan_file = protocol_root / "plan.md"
        context_file = protocol_root / "context.md"

        self.assertTrue(
            plan_file.is_file(),
            f"plan.md not found at expected location {plan_file}",
        )
        self.assertTrue(
            context_file.is_file(),
            f"context.md not found at expected location {context_file}",
        )
