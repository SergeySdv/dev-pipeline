class BudgetExceededError(ValueError):
    """Raised when estimated tokens exceed configured budget."""


class CodexCommandError(RuntimeError):
    """Raised when Codex execution fails."""


class GitCommandError(RuntimeError):
    """Raised when git commands fail."""


class CITriggerError(RuntimeError):
    """Raised when CI triggering via gh/glab fails."""
