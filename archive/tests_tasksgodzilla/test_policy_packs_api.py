import tempfile
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient  # type: ignore
    from tasksgodzilla.api.app import app
except ImportError:  # pragma: no cover - fastapi not installed in minimal envs
    TestClient = None  # type: ignore
    app = None  # type: ignore


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_policy_packs_seed_and_project_effective_policy(
    redis_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-test.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            # Default pack should be seeded on init_schema.
            packs = client.get("/policy_packs").json()
            assert any(p["key"] == "default" and p["version"] == "1.0" for p in packs)

            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = proj["id"]
            assert proj.get("policy_pack_key") == "default"

            # Set policy selection + overrides.
            upd = client.put(
                f"/projects/{project_id}/policy",
                json={
                    "policy_pack_key": "default",
                    "policy_pack_version": "1.0",
                    "policy_overrides": {"defaults": {"models": {"exec": "zai-coding-plan/glm-4.6"}}},
                    "policy_repo_local_enabled": False,
                },
            )
            assert upd.status_code == 200
            body = upd.json()
            assert body["project_id"] == project_id
            assert body["policy_pack_key"] == "default"
            assert body["policy_pack_version"] == "1.0"
            assert body["policy_overrides"]["defaults"]["models"]["exec"] == "zai-coding-plan/glm-4.6"
            assert body["policy_effective_hash"]

            eff = client.get(f"/projects/{project_id}/policy/effective").json()
            assert eff["project_id"] == project_id
            assert eff["policy_pack_key"] == "default"
            assert eff["policy_pack_version"] == "1.0"
            assert eff["policy"]["defaults"]["models"]["exec"] == "zai-coding-plan/glm-4.6"
            assert isinstance(eff["policy_effective_hash"], str) and len(eff["policy_effective_hash"]) >= 32

            findings = client.get(f"/projects/{project_id}/policy/findings").json()
            assert isinstance(findings, list)

            run = client.post(
                f"/projects/{project_id}/protocols",
                json={
                    "protocol_name": "0001-policy-demo",
                    "status": "planning",
                    "base_branch": "main",
                    "worktree_path": None,
                    "protocol_root": None,
                    "description": "policy demo",
                },
            ).json()
            assert run.get("policy_effective_hash")
            proto_findings = client.get(f"/protocols/{run['id']}/policy/findings").json()
            assert isinstance(proto_findings, list)
            snap = client.get(f"/protocols/{run['id']}/policy/snapshot").json()
            assert snap["protocol_run_id"] == run["id"]
            assert snap["policy_effective_hash"]
            assert isinstance(snap.get("policy_effective_json"), dict)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_step_policy_findings_from_step_file(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-step.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        protocol_root = Path(tmpdir) / ".protocols" / "0001-demo"
        protocol_root.mkdir(parents=True, exist_ok=True)
        # Intentionally omit required sections to trigger findings for beginner-guided pack.
        (protocol_root / "01-implement.md").write_text("# Step\n\nDo the thing.\n", encoding="utf-8")

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = proj["id"]
            client.put(
                f"/projects/{project_id}/policy",
                json={"policy_pack_key": "beginner-guided", "policy_pack_version": "1.0", "policy_repo_local_enabled": False},
            )

            run = client.post(
                f"/projects/{project_id}/protocols",
                json={
                    "protocol_name": "0001-demo",
                    "status": "running",
                    "base_branch": "main",
                    "worktree_path": str(Path(tmpdir)),
                    "protocol_root": str(protocol_root),
                    "description": "demo",
                },
            ).json()
            protocol_run_id = run["id"]

            step = client.post(
                f"/protocols/{protocol_run_id}/steps",
                json={"step_index": 1, "step_name": "01-implement", "step_type": "work", "status": "pending"},
            ).json()

            findings = client.get(f"/steps/{step['id']}/policy/findings").json()
            codes = {f["code"] for f in findings}
            assert "policy.step.missing_section" in codes


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_required_checks_findings_for_missing_scripts(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-checks.sqlite"
        repo_root = Path(tmpdir) / "repo"
        repo_root.mkdir(parents=True, exist_ok=True)

        # Create only one of the required checks; leave others missing.
        scripts_dir = repo_root / "scripts" / "ci"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "test.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")

        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                    "local_path": str(repo_root),
                },
            ).json()
            project_id = proj["id"]

            client.put(
                f"/projects/{project_id}/policy",
                json={"policy_pack_key": "beginner-guided", "policy_pack_version": "1.0", "policy_repo_local_enabled": False},
            )

            findings = client.get(f"/projects/{project_id}/policy/findings").json()
            codes = [f["code"] for f in findings]
            assert "policy.ci.required_check_missing" in codes


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_step_required_checks_findings_not_executable(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-step-checks.sqlite"
        repo_root = Path(tmpdir) / "repo"
        repo_root.mkdir(parents=True, exist_ok=True)

        scripts_dir = repo_root / "scripts" / "ci"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        check_path = scripts_dir / "test.sh"
        check_path.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
        # Intentionally do not chmod +x so it's non-executable.

        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        protocol_root = repo_root / ".protocols" / "0001-demo"
        protocol_root.mkdir(parents=True, exist_ok=True)
        (protocol_root / "01-implement.md").write_text("# Step\n\n## Verification\n\n- TBD\n", encoding="utf-8")

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                    "local_path": str(repo_root),
                },
            ).json()
            project_id = proj["id"]
            client.put(
                f"/projects/{project_id}/policy",
                json={"policy_pack_key": "beginner-guided", "policy_pack_version": "1.0", "policy_repo_local_enabled": False},
            )

            run = client.post(
                f"/projects/{project_id}/protocols",
                json={
                    "protocol_name": "0001-demo",
                    "status": "running",
                    "base_branch": "main",
                    "worktree_path": str(repo_root),
                    "protocol_root": str(protocol_root),
                    "description": "demo",
                },
            ).json()
            protocol_run_id = run["id"]
            step = client.post(
                f"/protocols/{protocol_run_id}/steps",
                json={"step_index": 1, "step_name": "01-implement", "step_type": "work", "status": "pending"},
            ).json()

            findings = client.get(f"/steps/{step['id']}/policy/findings").json()
            codes = [f["code"] for f in findings]
            assert "policy.ci.required_check_not_executable" in codes


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_repo_local_policy_override_is_applied(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-repo-local.sqlite"
        repo_root = Path(tmpdir) / "repo"
        repo_root.mkdir(parents=True, exist_ok=True)
        (repo_root / ".tasksgodzilla").mkdir(parents=True, exist_ok=True)
        (repo_root / ".tasksgodzilla" / "policy.json").write_text(
            '{"defaults":{"ci":{"required_checks":["scripts/ci/custom.sh"]}}}',
            encoding="utf-8",
        )

        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                    "local_path": str(repo_root),
                },
            ).json()
            project_id = proj["id"]

            client.put(
                f"/projects/{project_id}/policy",
                json={
                    "policy_pack_key": "beginner-guided",
                    "policy_pack_version": "1.0",
                    "policy_repo_local_enabled": True,
                },
            )

            eff = client.get(f"/projects/{project_id}/policy/effective").json()
            assert eff["sources"]["repo_local_applied"] is True
            assert eff["policy"]["defaults"]["ci"]["required_checks"] == ["scripts/ci/custom.sh"]
            assert "block_codes" in eff["policy"]["enforcement"]


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_policy_pack_exposes_block_codes(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-blockcodes.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            packs = client.get("/policy_packs").json()
            beginner = next(p for p in packs if p["key"] == "beginner-guided" and p["version"] == "1.0")
            assert "enforcement" in beginner["pack"]
            assert "block_codes" in beginner["pack"]["enforcement"]
            assert "policy.ci.required_check_missing" in beginner["pack"]["enforcement"]["block_codes"]


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_policy_enforcement_mode_escalates_severity(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-enforcement.sqlite"
        repo_root = Path(tmpdir) / "repo"
        repo_root.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                    "local_path": str(repo_root),
                },
            ).json()
            project_id = proj["id"]
            client.put(
                f"/projects/{project_id}/policy",
                json={
                    "policy_pack_key": "beginner-guided",
                    "policy_pack_version": "1.0",
                    "policy_repo_local_enabled": False,
                    "policy_enforcement_mode": "block",
                },
            )
            findings = client.get(f"/projects/{project_id}/policy/findings").json()
            assert findings
            missing = [f for f in findings if f["code"] == "policy.ci.required_check_missing"]
            assert missing
            assert all(f["severity"] == "block" for f in missing)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_strict_mode_does_not_escalate_all_warnings(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-enforcement2.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = proj["id"]
            # Force a non-blockable warning: repo-local enabled without local_path.
            client.put(
                f"/projects/{project_id}/policy",
                json={"policy_repo_local_enabled": True, "policy_enforcement_mode": "block"},
            )
            findings = client.get(f"/projects/{project_id}/policy/findings").json()
            repo_local = [f for f in findings if f["code"] == "policy.repo_local.no_local_path"]
            assert repo_local
            assert all(f["severity"] == "warning" for f in repo_local)


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_can_clear_policy_pack_version_to_use_latest(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-latest.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = proj["id"]

            # Create a newer active version for an existing pack key.
            newer = client.post(
                "/policy_packs",
                json={
                    "key": "beginner-guided",
                    "version": "2.0",
                    "name": "Beginner Guided",
                    "description": "Test newer version",
                    "status": "active",
                    "pack": {
                        "meta": {"key": "beginner-guided", "name": "Beginner Guided", "version": "2.0"},
                        "defaults": {},
                        "requirements": {},
                        "clarifications": [],
                        "enforcement": {"mode": "warn", "block_codes": ["policy.ci.required_check_missing"]},
                    },
                },
            )
            assert newer.status_code == 200

            client.put(
                f"/projects/{project_id}/policy",
                json={"policy_pack_key": "beginner-guided", "policy_pack_version": "1.0"},
            )
            eff = client.get(f"/projects/{project_id}/policy/effective").json()
            assert eff["policy_pack_key"] == "beginner-guided"
            assert eff["policy_pack_version"] == "1.0"

            # Explicitly clear the version to float to latest.
            client.put(f"/projects/{project_id}/policy", json={"clear_policy_pack_version": True})
            policy = client.get(f"/projects/{project_id}/policy").json()
            assert policy["policy_pack_key"] == "beginner-guided"
            assert policy["policy_pack_version"] is None

            eff2 = client.get(f"/projects/{project_id}/policy/effective").json()
            assert eff2["policy_pack_key"] == "beginner-guided"
            assert eff2["policy_pack_version"] == "2.0"


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_policy_pack_validation_rejects_invalid_pack(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-validate.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            resp = client.post(
                "/policy_packs",
                json={
                    "key": "custom",
                    "version": "1.0",
                    "name": "Custom",
                    "status": "active",
                    "pack": {"meta": {"key": "WRONG", "version": "1.0"}},
                },
            )
            assert resp.status_code == 400
            body = resp.json()
            assert "errors" in body.get("detail", {})


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_project_policy_rejects_invalid_overrides(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-overrides-validate.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = proj["id"]

            resp = client.put(
                f"/projects/{project_id}/policy",
                json={"policy_overrides": ["not-a-dict"]},
            )
            assert resp.status_code == 400
            assert "errors" in resp.json().get("detail", {})

            resp2 = client.put(
                f"/projects/{project_id}/policy",
                json={"policy_overrides": {"meta": {"key": "x"}}},
            )
            assert resp2.status_code == 400


@pytest.mark.skipif(TestClient is None, reason="fastapi not installed")
def test_project_policy_rejects_conflicting_clear_and_version(redis_env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "policy-clear-conflict.sqlite"
        monkeypatch.setenv("TASKSGODZILLA_DB_PATH", str(db_path))
        monkeypatch.delenv("TASKSGODZILLA_API_TOKEN", raising=False)

        with TestClient(app) as client:  # type: ignore[arg-type]
            proj = client.post(
                "/projects",
                json={
                    "name": "demo",
                    "git_url": "git@example.com/demo.git",
                    "base_branch": "main",
                },
            ).json()
            project_id = proj["id"]

            resp = client.put(
                f"/projects/{project_id}/policy",
                json={"clear_policy_pack_version": True, "policy_pack_version": "1.0"},
            )
            assert resp.status_code == 400
