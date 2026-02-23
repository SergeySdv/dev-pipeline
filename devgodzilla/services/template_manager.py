"""Template management for specifications, plans, and protocols."""

import re
import yaml
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from devgodzilla.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Template:
    """A reusable template for DevGodzilla operations."""
    id: str
    name: str
    description: str
    category: str  # "specification", "plan", "protocol", "checklist"
    content: str
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "content": self.content,
            "variables": self.variables,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        """Create template from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
            
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "specification"),
            content=data.get("content", ""),
            variables=data.get("variables", {}),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class TemplateManager:
    """Manages templates for DevGodzilla operations."""
    
    templates_dir: Path
    
    def __post_init__(self):
        self.templates_dir = Path(self.templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Template] = {}
    
    def list_templates(self, category: Optional[str] = None) -> List[Template]:
        """List all templates, optionally filtered by category."""
        templates = []
        
        # Load from files
        for ext in ["*.yaml", "*.yml", "*.json"]:
            for file_path in self.templates_dir.glob(ext):
                try:
                    template = self._load_template(file_path)
                    if template:
                        if category is None or template.category == category:
                            templates.append(template)
                except Exception as e:
                    logger.warning(
                        "template_load_failed",
                        extra={"file": str(file_path), "error": str(e)},
                    )
        
        # Include default templates
        for template_id, template_data in DEFAULT_TEMPLATES.items():
            # Don't add if already loaded from file
            if not any(t.id == template_id for t in templates):
                template = Template.from_dict(template_data)
                if category is None or template.category == category:
                    templates.append(template)
        
        # Sort by name
        templates.sort(key=lambda t: t.name)
        return templates
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """Get a template by ID."""
        # Check cache first
        if template_id in self._cache:
            return self._cache[template_id]
        
        # Check default templates
        if template_id in DEFAULT_TEMPLATES:
            return Template.from_dict(DEFAULT_TEMPLATES[template_id])
        
        # Try to load from file
        for ext in [".yaml", ".yml", ".json"]:
            file_path = self.templates_dir / f"{template_id}{ext}"
            if file_path.exists():
                template = self._load_template(file_path)
                if template:
                    self._cache[template_id] = template
                    return template
        
        return None
    
    def create_template(self, template: Template) -> Template:
        """Create a new template."""
        template.created_at = datetime.utcnow()
        template.updated_at = datetime.utcnow()
        
        file_path = self._save_template(template)
        self._cache[template.id] = template
        
        logger.info(
            "template_created",
            extra={"template_id": template.id, "file": str(file_path)},
        )
        
        return template
    
    def update_template(self, template_id: str, **updates) -> Optional[Template]:
        """Update an existing template."""
        template = self.get_template(template_id)
        if not template:
            return None
        
        # Don't allow updating id
        updates.pop("id", None)
        updates.pop("created_at", None)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        
        # Save to file (only for non-default templates)
        if template_id not in DEFAULT_TEMPLATES:
            self._save_template(template)
        
        # Update cache
        self._cache[template_id] = template
        
        logger.info(
            "template_updated",
            extra={"template_id": template_id, "updates": list(updates.keys())},
        )
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        # Can't delete default templates
        if template_id in DEFAULT_TEMPLATES:
            logger.warning(
                "cannot_delete_default_template",
                extra={"template_id": template_id},
            )
            return False
        
        # Find and delete file
        for ext in [".yaml", ".yml", ".json"]:
            file_path = self.templates_dir / f"{template_id}{ext}"
            if file_path.exists():
                file_path.unlink()
                self._cache.pop(template_id, None)
                logger.info(
                    "template_deleted",
                    extra={"template_id": template_id},
                )
                return True
        
        return False
    
    def render_template(self, template_id: str, variables: Dict[str, Any]) -> str:
        """Render a template with variables."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Validate required variables
        template_vars = template.variables or {}
        for var_name, var_config in template_vars.items():
            if var_config.get("required", False) and var_name not in variables:
                default = var_config.get("default")
                if default is None:
                    raise ValueError(f"Missing required variable: {var_name}")
                variables[var_name] = default
        
        # Apply defaults for missing optional variables
        for var_name, var_config in template_vars.items():
            if var_name not in variables and "default" in var_config:
                variables[var_name] = var_config["default"]
        
        # Render content using simple string formatting
        content = template.content
        
        # Handle list variables (join with newlines and bullets)
        render_vars = {}
        for key, value in variables.items():
            if isinstance(value, list):
                render_vars[key] = "\n".join(f"- {item}" for item in value)
            elif isinstance(value, dict):
                render_vars[key] = yaml.dump(value, default_flow_style=False)
            else:
                render_vars[key] = str(value) if value is not None else ""
        
        # Use safe substitution with braces
        try:
            content = content.format(**render_vars)
        except KeyError as e:
            raise ValueError(f"Missing variable in template: {e}")
        
        return content
    
    def import_template(self, file_path: Path) -> Template:
        """Import a template from a file."""
        template = self._load_template(file_path)
        if not template:
            raise ValueError(f"Failed to load template from: {file_path}")
        
        # Save to templates directory
        self._save_template(template)
        self._cache[template.id] = template
        
        logger.info(
            "template_imported",
            extra={"template_id": template.id, "source": str(file_path)},
        )
        
        return template
    
    def export_template(self, template_id: str, output_path: Path) -> Path:
        """Export a template to a file."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine format from extension
        suffix = output_path.suffix.lower()
        if suffix in [".yaml", ".yml"]:
            content = yaml.dump(template.to_dict(), default_flow_style=False, sort_keys=False)
        else:
            content = json.dumps(template.to_dict(), indent=2)
        
        output_path.write_text(content)
        
        logger.info(
            "template_exported",
            extra={"template_id": template_id, "output": str(output_path)},
        )
        
        return output_path
    
    def _load_template(self, file_path: Path) -> Optional[Template]:
        """Load template from YAML or JSON file."""
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text()
            suffix = file_path.suffix.lower()
            
            if suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(content)
            elif suffix == ".json":
                data = json.loads(content)
            else:
                return None
            
            if not isinstance(data, dict) or "id" not in data:
                return None
            
            return Template.from_dict(data)
        except Exception as e:
            logger.error(
                "template_parse_error",
                extra={"file": str(file_path), "error": str(e)},
            )
            return None
    
    def _save_template(self, template: Template) -> Path:
        """Save template to file."""
        # Use YAML by default
        file_path = self.templates_dir / f"{template.id}.yaml"
        
        data = template.to_dict()
        content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        
        file_path.write_text(content)
        return file_path


# Default templates
DEFAULT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "feature-spec": {
        "id": "feature-spec",
        "name": "Feature Specification",
        "description": "Template for feature specifications",
        "category": "specification",
        "content": """# {feature_name}

## Overview
{description}

## User Stories
{user_stories}

## Acceptance Criteria
{acceptance_criteria}

## Technical Notes
{technical_notes}
""",
        "variables": {
            "feature_name": {"type": "string", "required": True},
            "description": {"type": "string", "required": True},
            "user_stories": {"type": "list", "required": False, "default": []},
            "acceptance_criteria": {"type": "list", "required": False, "default": []},
            "technical_notes": {"type": "string", "required": False, "default": ""}
        }
    },
    "api-endpoint": {
        "id": "api-endpoint",
        "name": "API Endpoint",
        "description": "Template for API endpoint implementation",
        "category": "protocol",
        "content": """## {method} {path}

### Description
{description}

### Request
{request_schema}

### Response
{response_schema}

### Implementation Steps
1. Validate request
2. Process business logic
3. Return response
""",
        "variables": {
            "method": {"type": "string", "required": True, "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
            "path": {"type": "string", "required": True},
            "description": {"type": "string", "required": True},
            "request_schema": {"type": "object", "required": False},
            "response_schema": {"type": "object", "required": False}
        }
    },
    "bug-fix": {
        "id": "bug-fix",
        "name": "Bug Fix",
        "description": "Template for bug fix protocols",
        "category": "protocol",
        "content": """# Bug Fix: {bug_title}

## Description
{description}

## Steps to Reproduce
{steps_to_reproduce}

## Expected Behavior
{expected_behavior}

## Actual Behavior
{actual_behavior}

## Root Cause Analysis
{root_cause}

## Fix Implementation
{implementation}

## Testing
{testing_notes}
""",
        "variables": {
            "bug_title": {"type": "string", "required": True},
            "description": {"type": "string", "required": True},
            "steps_to_reproduce": {"type": "list", "required": False, "default": []},
            "expected_behavior": {"type": "string", "required": False, "default": ""},
            "actual_behavior": {"type": "string", "required": False, "default": ""},
            "root_cause": {"type": "string", "required": False, "default": ""},
            "implementation": {"type": "string", "required": False, "default": ""},
            "testing_notes": {"type": "string", "required": False, "default": ""}
        }
    },
    "implementation-plan": {
        "id": "implementation-plan",
        "name": "Implementation Plan",
        "description": "Template for creating implementation plans",
        "category": "plan",
        "content": """# Implementation Plan: {feature_name}

## Summary
{summary}

## Prerequisites
{prerequisites}

## Steps
{steps}

## Dependencies
{dependencies}

## Risks and Mitigations
{risks}

## Timeline
{timeline}
""",
        "variables": {
            "feature_name": {"type": "string", "required": True},
            "summary": {"type": "string", "required": True},
            "prerequisites": {"type": "list", "required": False, "default": []},
            "steps": {"type": "list", "required": False, "default": []},
            "dependencies": {"type": "list", "required": False, "default": []},
            "risks": {"type": "list", "required": False, "default": []},
            "timeline": {"type": "string", "required": False, "default": ""}
        }
    },
    "quality-checklist": {
        "id": "quality-checklist",
        "name": "Quality Checklist",
        "description": "Template for quality assurance checklists",
        "category": "checklist",
        "content": """# Quality Checklist: {feature_name}

## Code Quality
- [ ] Code follows project style guidelines
- [ ] No hardcoded values (use constants/config)
- [ ] Error handling is comprehensive
- [ ] Code is well-documented

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Edge cases covered
- [ ] No test regressions

## Security
- [ ] No sensitive data in logs
- [ ] Input validation implemented
- [ ] Authentication/authorization correct
- [ ] No SQL injection vulnerabilities

## Performance
- [ ] No N+1 queries
- [ ] Appropriate indexes exist
- [ ] Caching considered
- [ ] Response times acceptable

## Documentation
- [ ] API documentation updated
- [ ] README updated if needed
- [ ] Change log entry added
- [ ] Comments explain complex logic

## Notes
{notes}
""",
        "variables": {
            "feature_name": {"type": "string", "required": True},
            "notes": {"type": "string", "required": False, "default": ""}
        }
    }
}


def create_default_templates(templates_dir: Path) -> None:
    """Create default templates in the templates directory."""
    manager = TemplateManager(templates_dir)
    
    for template_id, template_data in DEFAULT_TEMPLATES.items():
        file_path = templates_dir / f"{template_id}.yaml"
        
        # Don't overwrite existing templates
        if file_path.exists():
            continue
        
        template = Template.from_dict(template_data)
        manager._save_template(template)
        logger.info(
            "default_template_created",
            extra={"template_id": template_id, "file": str(file_path)},
        )


def get_template_manager(templates_dir: Optional[Path] = None) -> TemplateManager:
    """Get a template manager instance."""
    if templates_dir is None:
        # Default to config directory
        from devgodzilla.config import get_config
        config = get_config()
        templates_dir = Path(config.config_dir) / "templates"
    
    return TemplateManager(templates_dir)
