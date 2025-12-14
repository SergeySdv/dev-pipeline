import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from tasksgodzilla.engines import EngineMetadata, EngineRequest, EngineResult, registry
from tasksgodzilla.errors import ConfigError, OpenCodeCommandError


def _join_base_url(base_url: str, path: str) -> str:
    base = (base_url or "").rstrip("/")
    suffix = (path or "").lstrip("/")
    return f"{base}/{suffix}"


def _normalize_model(model: str) -> str:
    """
    Normalize common aliases across OpenCode providers.

    OpenCode's CLI model catalog may not include a plain `zai/*` provider. In
    practice, GLM models are commonly exposed as:
    - zai-coding-plan/glm-4.6  (provider: "Z.AI Coding Plan")
    - chutes/zai-org/GLM-4.6
    """
    val = (model or "").strip()
    if not val:
        return val
    # Back-compat alias.
    if val.lower().startswith("zai/"):
        return "zai-coding-plan/" + val.split("/", 1)[1]
    return val


class OpenCodeEngine:
    """
    Engine wrapper for OpenCode via an OpenAI-compatible HTTP API.

    Defaults align with OpenCode Zen docs:
    - base URL: https://opencode.ai/zen/v1
    - chat completions: POST /chat/completions
    - model examples: zai-coding-plan/glm-4.6 (provider: "Z.AI Coding Plan")
    """

    metadata = EngineMetadata(
        id="opencode",
        display_name="OpenCode (OpenAI-compatible)",
        kind="api",
        default_model="zai-coding-plan/glm-4.6",
    )

    def _api_config(self) -> tuple[str, str]:
        base_url = os.environ.get("TASKSGODZILLA_OPENCODE_BASE_URL", "https://opencode.ai/zen/v1").strip()
        api_key = os.environ.get("TASKSGODZILLA_OPENCODE_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "TASKSGODZILLA_OPENCODE_API_KEY is required to use engine_id=opencode",
                metadata={"engine_id": self.metadata.id},
            )
        if not base_url:
            raise ConfigError(
                "TASKSGODZILLA_OPENCODE_BASE_URL is empty",
                metadata={"engine_id": self.metadata.id},
            )
        return base_url, api_key

    def _prompt_text(self, req: EngineRequest) -> str:
        extra: dict[str, Any] = dict(req.extra or {})
        prompt_from_extra = extra.get("prompt_text")
        if isinstance(prompt_from_extra, str) and prompt_from_extra:
            prompt_text = prompt_from_extra
        else:
            parts: list[str] = []
            for p in req.prompt_files:
                try:
                    parts.append(Path(p).read_text(encoding="utf-8"))
                except FileNotFoundError:
                    continue
            prompt_text = "\n".join(parts)

        output_schema = extra.get("output_schema")
        if output_schema:
            try:
                schema_text = Path(str(output_schema)).read_text(encoding="utf-8")
                prompt_text += (
                    "\n\n"
                    "Return ONLY a single JSON object that conforms to this JSON Schema. "
                    "Do not include Markdown fences, prose, or extra keys.\n\n"
                    f"JSON Schema:\n{schema_text}\n"
                )
            except Exception:
                # Best-effort: if schema can't be read, still proceed.
                pass
        return prompt_text

    def _call_via_api(self, req: EngineRequest, *, purpose: str) -> EngineResult:
        base_url, api_key = self._api_config()
        model = _normalize_model(req.model or self.metadata.default_model or "")
        if not model:
            raise ConfigError("OpenCodeEngine requires a model", metadata={"engine_id": self.metadata.id})

        extra: dict[str, Any] = dict(req.extra or {})
        prompt_text = self._prompt_text(req)

        timeout_seconds = extra.get("timeout_seconds")
        if not isinstance(timeout_seconds, int):
            try:
                timeout_seconds = int(os.environ.get("TASKSGODZILLA_OPENCODE_TIMEOUT_SECONDS", "180"))
            except Exception:
                timeout_seconds = 180

        url = _join_base_url(base_url, "/chat/completions")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": float(extra.get("temperature", 0.0)),
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=float(timeout_seconds)) as client:
                resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            body = ""
            try:
                body = exc.response.text
            except Exception:
                body = ""
            raise OpenCodeCommandError(
                f"OpenCode request failed ({exc.response.status_code})",
                metadata={
                    "engine_id": self.metadata.id,
                    "purpose": purpose,
                    "status_code": exc.response.status_code,
                    "url": url,
                    "response_text": body[:2000],
                },
            ) from exc
        except Exception as exc:
            raise OpenCodeCommandError(
                f"OpenCode request failed: {exc}",
                metadata={"engine_id": self.metadata.id, "purpose": purpose, "url": url},
            ) from exc

        content = ""
        try:
            choices = data.get("choices") or []
            if choices:
                msg = (choices[0] or {}).get("message") or {}
                content = (msg.get("content") or "") if isinstance(msg, dict) else ""
        except Exception:
            content = ""

        if not isinstance(content, str) or not content.strip():
            raise OpenCodeCommandError(
                "OpenCode returned empty content",
                metadata={"engine_id": self.metadata.id, "purpose": purpose, "url": url, "response": data},
            )

        usage = data.get("usage") if isinstance(data, dict) else None
        tokens_used = None
        if isinstance(usage, dict):
            try:
                tokens_used = int(usage.get("total_tokens")) if usage.get("total_tokens") is not None else None
            except Exception:
                tokens_used = None

        return EngineResult(
            success=True,
            stdout=content,
            stderr="",
            tokens_used=tokens_used,
            cost=None,
            metadata={
                "engine_id": self.metadata.id,
                "purpose": purpose,
                "invocation": "api",
                "base_url": base_url,
                "model": model,
            },
        )

    def _call_via_cli(self, req: EngineRequest, *, purpose: str) -> EngineResult:
        model = _normalize_model(req.model or self.metadata.default_model or "")
        if not model:
            raise ConfigError("OpenCodeEngine requires a model", metadata={"engine_id": self.metadata.id})
        if shutil.which("opencode") is None:
            raise ConfigError(
                "opencode CLI not found in PATH and TASKSGODZILLA_OPENCODE_API_KEY not set",
                metadata={"engine_id": self.metadata.id},
            )

        extra: dict[str, Any] = dict(req.extra or {})
        prompt_text = self._prompt_text(req)

        timeout_seconds = extra.get("timeout_seconds")
        if not isinstance(timeout_seconds, int):
            try:
                timeout_seconds = int(os.environ.get("TASKSGODZILLA_OPENCODE_TIMEOUT_SECONDS", "180"))
            except Exception:
                timeout_seconds = 180
        # OpenCode CLI can be long-running. We support "chunked" execution by running
        # multiple `opencode run --continue` invocations until we get a final answer
        # or hit the overall timeout budget. This avoids relying on API keys.
        try:
            chunk_timeout = int(os.environ.get("TASKSGODZILLA_OPENCODE_CHUNK_TIMEOUT_SECONDS", "240"))
        except Exception:
            chunk_timeout = 240
        chunk_timeout = max(60, chunk_timeout)
        total_budget = max(int(timeout_seconds), chunk_timeout)
        max_attempts = min(50, (total_budget // chunk_timeout) + 3)

        workdir = Path(req.working_dir or ".").resolve()
        workdir.mkdir(parents=True, exist_ok=True)

        tmp_path: Path
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", dir=str(workdir), encoding="utf-8") as f:
            f.write(prompt_text)
            tmp_path = Path(f.name)

        # Use OpenCode's stored provider credentials from the user's profile.
        # For GLM-4.6 this is typically provider "Z.AI Coding Plan" (model prefix: zai-coding-plan/*).
        # We attach the full prompt as a file to avoid command-line length limits.
        initial_message = "Use the attached file as the full prompt. Follow it exactly. Output only the final answer."
        continue_message = (
            "Continue the prior session and finish the task. "
            "Use the attached file as the full prompt/context. Output only the final answer."
        )
        try:
            proc: subprocess.CompletedProcess[str] | None = None
            last_cmd: list[str] | None = None
            start = time.time()
            for attempt in range(max_attempts):
                if time.time() - start > total_budget:
                    break
                msg = initial_message if attempt == 0 else continue_message
                cmd = [
                    "opencode",
                    "run",
                    msg,
                    "--model",
                    model,
                    "--format",
                    "default",
                    "--file",
                    str(tmp_path),
                ]
                if attempt > 0:
                    cmd.append("--continue")
                last_cmd = cmd
                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=str(workdir),
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=chunk_timeout,
                    )
                except subprocess.TimeoutExpired:
                    # If a chunk times out, continue the session and keep going
                    # until we hit the overall budget.
                    continue
                if proc.returncode == 0 and (proc.stdout or "").strip():
                    break
                combined = ((proc.stdout or "") + "\n" + (proc.stderr or "")).lower()
                retryable = ("timeout" in combined) or ("timed out" in combined) or ("exceeded maximum timeout" in combined)
                if not retryable or attempt >= (max_attempts - 1):
                    break
                # brief backoff before continuing the session
                time.sleep(1.0 + attempt * 0.5)
        except Exception as exc:
            raise OpenCodeCommandError(
                f"OpenCode CLI failed: {exc}",
                metadata={
                    "engine_id": self.metadata.id,
                    "purpose": purpose,
                    "cmd": last_cmd or [],
                    "cwd": str(workdir),
                },
            ) from exc
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        if proc is None:
            raise OpenCodeCommandError(
                "OpenCode CLI failed: no output produced before timeout budget was exhausted",
                metadata={
                    "engine_id": self.metadata.id,
                    "purpose": purpose,
                    "cmd": last_cmd or [],
                    "cwd": str(workdir),
                    "timeout_seconds": int(timeout_seconds),
                    "chunk_timeout_seconds": chunk_timeout,
                    "max_attempts": max_attempts,
                },
            )

        if proc.returncode != 0:
            stderr_snip = (proc.stderr or "").strip().splitlines()[-1] if (proc.stderr or "").strip() else ""
            stdout_snip = (proc.stdout or "").strip().splitlines()[-1] if (proc.stdout or "").strip() else ""
            detail = stderr_snip or stdout_snip
            raise OpenCodeCommandError(
                f"OpenCode CLI failed: {detail}" if detail else f"OpenCode CLI failed (rc={proc.returncode})",
                metadata={
                    "engine_id": self.metadata.id,
                    "purpose": purpose,
                    "cmd": last_cmd or [],
                    "cwd": str(workdir),
                    "stdout": (proc.stdout or "")[:2000],
                    "stderr": (proc.stderr or "")[:2000],
                    "returncode": proc.returncode,
                },
            )

        content = (proc.stdout or "").strip()
        if not content:
            raise OpenCodeCommandError(
                "OpenCode CLI returned empty output",
                metadata={"engine_id": self.metadata.id, "purpose": purpose, "cmd": cmd, "cwd": str(workdir)},
            )

        return EngineResult(
            success=True,
            stdout=content,
            stderr=proc.stderr or "",
            tokens_used=None,
            cost=None,
            metadata={
                "engine_id": self.metadata.id,
                "purpose": purpose,
                "invocation": "cli",
                "model": model,
                "returncode": proc.returncode,
            },
        )

    def _call(self, req: EngineRequest, *, purpose: str) -> EngineResult:
        # Prefer API when explicitly configured; otherwise fallback to OpenCode CLI
        # which uses stored user-profile credentials (e.g. provider zai).
        if os.environ.get("TASKSGODZILLA_OPENCODE_API_KEY", "").strip():
            return self._call_via_api(req, purpose=purpose)
        return self._call_via_cli(req, purpose=purpose)

    def plan(self, req: EngineRequest) -> EngineResult:
        return self._call(req, purpose="plan")

    def execute(self, req: EngineRequest) -> EngineResult:
        return self._call(req, purpose="execute")

    def qa(self, req: EngineRequest) -> EngineResult:
        return self._call(req, purpose="qa")

    def sync_config(self, additional_agents=None) -> None:  # pragma: no cover
        return None


def register_opencode_engine() -> None:
    registry.register(OpenCodeEngine(), default=False)


# Register on import so services relying on the registry can select it.
register_opencode_engine()

