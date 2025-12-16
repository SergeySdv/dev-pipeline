"""
Clone Repository Script

Clones a GitHub repository to a workspace directory.

Args:
    repo_url: GitHub repository URL (e.g., https://github.com/user/repo)
    branch: Branch to clone (default: main)
    workspace_path: Optional custom path, defaults to /tmp/devgodzilla/repos/<repo_name>

Returns:
    success: Whether clone succeeded
    path: Local path where repo was cloned
    commit: Latest commit SHA
"""

import subprocess
import os
import re
from pathlib import Path


def main(
    repo_url: str,
    branch: str = "main",
    workspace_path: str = "",
) -> dict:
    """Clone a GitHub repository."""
    
    # Extract repo name from URL
    match = re.search(r'/([^/]+?)(?:\.git)?$', repo_url)
    if not match:
        return {"success": False, "error": f"Invalid repo URL: {repo_url}"}
    
    repo_name = match.group(1)
    
    # Determine target path
    if workspace_path:
        target_path = Path(workspace_path)
    else:
        target_path = Path("/tmp/devgodzilla/repos") / repo_name
    
    # Create parent directory if needed
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing directory if present
    if target_path.exists():
        import shutil
        shutil.rmtree(target_path)
    
    # Clone the repository
    try:
        result = subprocess.run(
            ["git", "clone", "--branch", branch, "--single-branch", "--depth", "100", repo_url, str(target_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or "Clone failed",
                "path": str(target_path),
            }
        
        # Get latest commit
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(target_path),
            capture_output=True,
            text=True,
        )
        commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
        
        return {
            "success": True,
            "path": str(target_path),
            "commit": commit,
            "repo_name": repo_name,
            "branch": branch,
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Clone timed out after 5 minutes"}
    except Exception as e:
        return {"success": False, "error": str(e)}
