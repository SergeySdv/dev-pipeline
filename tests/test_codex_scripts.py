import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Allow importing the CLI scripts as modules
ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import codex_ci_bootstrap  # type: ignore  # noqa: E402
import protocol_pipeline  # type: ignore  # noqa: E402
import quality_orchestrator  # type: ignore  # noqa: E402
import project_setup  # type: ignore  # noqa: E402


class DummyResult:
    def __init__(self, args, stdout: str = "", returncode: int = 0):
        self.args = args
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class CodexScriptTests(unittest.TestCase):
    def test_codex_ci_bootstrap_invokes_codex_exec_with_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            prompt_file = tmp_path / "prompt.md"
            prompt_file.write_text("hello from prompt", encoding="utf-8")

            captured = {}

            def fake_run(cmd, cwd=None, check=True, input_text=None):
                captured["cmd"] = cmd
                captured["cwd"] = cwd
                captured["input_text"] = input_text
                return DummyResult(cmd)

            argv = [
                "codex_ci_bootstrap.py",
                "--model",
                "test-model",
                "--prompt-file",
                str(prompt_file),
                "--repo-root",
                str(tmp_path),
                "--sandbox",
                "workspace-write",
                "--skip-git-check",
            ]

            with mock.patch.object(codex_ci_bootstrap.shutil, "which", return_value="/usr/bin/codex"), \
                mock.patch.object(codex_ci_bootstrap, "run", side_effect=fake_run), \
                mock.patch.object(sys, "argv", argv):
                codex_ci_bootstrap.main()

            self.assertEqual(captured["cmd"][:4], ["codex", "exec", "-m", "test-model"])
            self.assertIsNone(captured["cwd"])
            self.assertEqual(captured["input_text"], "hello from prompt")

    def test_run_codex_exec_builds_command_with_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            schema = tmp_path / "schema.json"
            out_msg = tmp_path / "last.json"

            with mock.patch.object(protocol_pipeline.subprocess, "run") as mock_run:
                protocol_pipeline.run_codex_exec(
                    model="model-x",
                    cwd=tmp_path,
                    prompt_text="prompt-body",
                    sandbox="workspace-write",
                    output_schema=schema,
                    output_last_message=out_msg,
                )

            args, kwargs = mock_run.call_args
            cmd = args[0]
            self.assertEqual(cmd[:4], ["codex", "exec", "-m", "model-x"])
            self.assertIn("--output-schema", cmd)
            self.assertIn(str(schema), cmd)
            self.assertIn("--output-last-message", cmd)
            self.assertIn(str(out_msg), cmd)
            self.assertEqual(kwargs["input"], b"prompt-body")
            self.assertTrue(kwargs["check"])

    def test_quality_orchestrator_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            proto_root = Path(tmpdir) / ".protocols" / "0001-demo"
            proto_root.mkdir(parents=True, exist_ok=True)
            (proto_root / "plan.md").write_text("plan body", encoding="utf-8")
            (proto_root / "context.md").write_text("context body", encoding="utf-8")
            (proto_root / "log.md").write_text("log body", encoding="utf-8")
            step = proto_root / "01-step.md"
            step.write_text("step body", encoding="utf-8")

            codex_calls = []

            def fake_run(cmd, cwd=None, check=True, capture=True, input_text=None):
                if cmd[:2] == ["git", "status"]:
                    return DummyResult(cmd, stdout=" M file\n")
                if cmd[:2] == ["git", "log"]:
                    return DummyResult(cmd, stdout="commit msg")
                if cmd[0] == "codex":
                    codex_calls.append((cmd, input_text))
                    return DummyResult(cmd, stdout="VERDICT: PASS")
                raise AssertionError(f"Unexpected command: {cmd}")

            argv = [
                "quality_orchestrator.py",
                "--protocol-root",
                str(proto_root),
                "--step-file",
                "01-step.md",
                "--model",
                "test-model",
                "--sandbox",
                "read-only",
            ]

            with mock.patch.object(quality_orchestrator.shutil, "which", return_value="/usr/bin/codex"), \
                mock.patch.object(quality_orchestrator, "run", side_effect=fake_run), \
                mock.patch.object(sys, "argv", argv):
                quality_orchestrator.main()

            report_path = proto_root / "quality-report.md"
            self.assertTrue(report_path.is_file())
            self.assertIn("VERDICT: PASS", report_path.read_text(encoding="utf-8"))
            self.assertEqual(codex_calls[0][0][3], "test-model")

    def test_project_setup_codex_discovery_passes_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            prompts_dir = repo_root / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            prompt_file = prompts_dir / "repo-discovery.prompt.md"
            prompt_file.write_text("hello discovery", encoding="utf-8")

            captured = {}

            def fake_run(cmd, cwd=None, check=True, capture=True, input_text=None):
                captured["cmd"] = cmd
                captured["cwd"] = cwd
                captured["input_text"] = input_text
                return DummyResult(cmd)

            with mock.patch.object(project_setup.shutil, "which", return_value="/usr/bin/codex"), \
                mock.patch.object(project_setup, "run", side_effect=fake_run):
                project_setup.run_codex_discovery(repo_root, "gpt-5.1-codex-max")

            self.assertEqual(captured["cmd"][:4], ["codex", "exec", "-m", "gpt-5.1-codex-max"])
            self.assertEqual(captured["cwd"], repo_root)
            self.assertEqual(captured["input_text"], "hello discovery")


if __name__ == "__main__":
    unittest.main()
