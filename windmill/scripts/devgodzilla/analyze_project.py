"""
Analyze Project Script

Analyzes a project's structure, detecting language, framework, and key files.

Args:
    project_path: Path to the project directory

Returns:
    language: Primary programming language
    framework: Detected framework (if any)
    files: Important files found
    structure: Directory structure summary
"""

import os
from pathlib import Path
from collections import Counter


# File extension to language mapping
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
}

# Framework detection patterns
FRAMEWORK_INDICATORS = {
    "python": {
        "django": ["manage.py", "django"],
        "flask": ["flask", "app.py"],
        "fastapi": ["fastapi", "main.py"],
        "click": ["click", "setup.py", "pyproject.toml"],
        "pytest": ["pytest", "conftest.py"],
    },
    "javascript": {
        "react": ["react", "package.json"],
        "vue": ["vue", "package.json"],
        "nextjs": ["next.config", "package.json"],
        "express": ["express", "app.js"],
    },
    "typescript": {
        "nestjs": ["nestjs", "@nestjs"],
        "angular": ["angular.json", "@angular"],
    },
}

# Important files to look for
IMPORTANT_FILES = [
    "README.md",
    "README.rst",
    "setup.py",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    ".github/workflows",
    "requirements.txt",
    "poetry.lock",
    "LICENSE",
    "CONTRIBUTING.md",
]


def main(project_path: str) -> dict:
    """Analyze a project's structure."""
    
    path = Path(project_path)
    if not path.exists():
        return {"error": f"Path does not exist: {project_path}"}
    
    if not path.is_dir():
        return {"error": f"Path is not a directory: {project_path}"}
    
    # Count file extensions
    extension_counts = Counter()
    all_files = []
    
    for root, dirs, files in os.walk(path):
        # Skip hidden directories and common non-source dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in (
            "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".git"
        )]
        
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(path)
            all_files.append(str(rel_path))
            
            ext = file_path.suffix.lower()
            if ext in LANGUAGE_MAP:
                extension_counts[ext] += 1
    
    # Determine primary language
    primary_language = "unknown"
    if extension_counts:
        most_common_ext = extension_counts.most_common(1)[0][0]
        primary_language = LANGUAGE_MAP.get(most_common_ext, "unknown")
    
    # Detect framework
    detected_framework = None
    if primary_language in FRAMEWORK_INDICATORS:
        # Read key files for framework detection
        readme_content = ""
        readme_path = path / "README.md"
        if readme_path.exists():
            try:
                readme_content = readme_path.read_text(errors="ignore").lower()
            except:
                pass
        
        for framework, indicators in FRAMEWORK_INDICATORS[primary_language].items():
            for indicator in indicators:
                indicator_lower = indicator.lower()
                if indicator_lower in readme_content:
                    detected_framework = framework
                    break
                if (path / indicator).exists():
                    detected_framework = framework
                    break
            if detected_framework:
                break
    
    # Find important files
    found_important = []
    for important in IMPORTANT_FILES:
        if (path / important).exists():
            found_important.append(important)
        elif "/" in important:
            # Check for directory patterns
            if (path / important).parent.exists():
                found_important.append(important)
    
    # Build structure summary
    top_level = []
    for item in sorted(path.iterdir()):
        if item.name.startswith('.'):
            continue
        if item.is_dir():
            top_level.append(f"{item.name}/")
        else:
            top_level.append(item.name)
    
    return {
        "language": primary_language,
        "framework": detected_framework,
        "files": found_important,
        "structure": {
            "top_level": top_level[:30],  # Limit to 30 items
            "total_files": len(all_files),
            "file_extensions": dict(extension_counts.most_common(10)),
        },
        "project_name": path.name,
        "path": str(path),
    }
