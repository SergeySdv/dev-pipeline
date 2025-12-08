from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from tasksgodzilla.prompt_utils import prompt_version


@dataclass
class PromptService:
    """Minimal prompt helper facade.

    This service focuses on resolving prompt files under a workspace root and
    attaching a stable version fingerprint. Higher-level naming and policy can
    be added later without changing call sites.
    """

    workspace_root: Path

    def resolve(self, relative_path: str) -> Tuple[Path, str, str]:
        """Return (path, text, version_hash) for the given prompt path."""
        path = (self.workspace_root / relative_path).resolve()
        text = path.read_text(encoding="utf-8")
        version = prompt_version(path)
        return path, text, version

