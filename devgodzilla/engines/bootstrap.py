"""
DevGodzilla Engine Bootstrap

Helpers to ensure a usable engine registry in all entrypoints (API, CLI, Windmill workers).
"""

from __future__ import annotations

from devgodzilla.config import get_config
from devgodzilla.engines.registry import get_registry
from devgodzilla.engines.claude_code import ClaudeCodeEngine
from devgodzilla.engines.codex import CodexEngine
from devgodzilla.engines.dummy import DummyEngine
from devgodzilla.engines.opencode import OpenCodeEngine
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


def bootstrap_default_engines(*, replace: bool = True) -> None:
    """
    Register the standard set of engines.

    Always registers DummyEngine as the default so the system can run in dev stacks
    where agent CLIs are not installed.
    """
    registry = get_registry()

    def _register(engine, *, default: bool) -> None:
        if replace or not registry.has(engine.metadata.id):
            registry.register(engine, default=default, replace=replace)

    _register(DummyEngine(), default=True)
    _register(OpenCodeEngine(), default=False)
    _register(CodexEngine(), default=False)
    _register(ClaudeCodeEngine(), default=False)

    # In local/dev stacks we keep Dummy as the registry default for safety and to
    # keep tests deterministic.
    if not replace:
        if registry.has("dummy"):
            try:
                registry.set_default("dummy")
            except Exception:
                pass
    else:
        # When bootstrapping with `replace=True` (API entry), prefer the configured
        # default engine when it's actually available.
        try:
            preferred = (get_config().default_engine_id or "").strip() or "opencode"
        except Exception:
            preferred = "opencode"

        candidates = [preferred, "opencode", "codex", "claude-code", "dummy"]
        for engine_id in candidates:
            if not registry.has(engine_id):
                continue
            try:
                engine = registry.get(engine_id)
                if engine_id == "dummy" or engine.check_availability():
                    registry.set_default(engine_id)
                    break
            except Exception:
                continue

    logger.info(
        "engines_bootstrapped",
        extra={"engines": registry.list_ids(), "default": registry.get_default().metadata.id},
    )
