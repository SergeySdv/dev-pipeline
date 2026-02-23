"""Integration tests for template management."""

import pytest
from pathlib import Path

from devgodzilla.services.template_manager import TemplateManager, Template, DEFAULT_TEMPLATES


class TestTemplateFlowIntegration:
    """Tests for template management flow."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        return TemplateManager(templates_dir=tmp_path / "templates")
    
    def test_manager_initialization(self, manager):
        """TemplateManager initializes correctly."""
        assert manager.templates_dir.exists()
    
    def test_list_default_templates(self, manager):
        """Can list default templates."""
        templates = manager.list_templates()
        
        # Should include default templates
        assert len(templates) >= len(DEFAULT_TEMPLATES)
    
    def test_create_and_retrieve_template(self, manager):
        """Can create and retrieve a template."""
        template = Template(
            id="test-template",
            name="Test Template",
            description="A test template",
            category="specification",
            content="# {title}\n\n{description}"
        )
        
        created = manager.create_template(template)
        retrieved = manager.get_template("test-template")
        
        assert retrieved is not None
        assert retrieved.name == "Test Template"
    
    def test_render_template(self, manager):
        """Template rendering works with variables."""
        template = Template(
            id="render-test",
            name="Render Test",
            description="Test",
            category="test",
            content="Hello, {name}!",
            variables={"name": {"type": "string"}}
        )
        
        manager.create_template(template)
        rendered = manager.render_template("render-test", {"name": "World"})
        
        assert rendered == "Hello, World!"
    
    def test_render_template_with_defaults(self, manager):
        """Template rendering uses defaults for missing variables."""
        template = Template(
            id="defaults-test",
            name="Defaults Test",
            description="Test",
            category="test",
            content="Value: {value}",
            variables={"value": {"type": "string", "default": "default-value"}}
        )
        
        manager.create_template(template)
        rendered = manager.render_template("defaults-test", {})
        
        assert rendered == "Value: default-value"
    
    def test_render_template_missing_required(self, manager):
        """Template rendering raises on missing required variables."""
        template = Template(
            id="required-test",
            name="Required Test",
            description="Test",
            category="test",
            content="{required}",
            variables={"required": {"type": "string", "required": True}}
        )
        
        manager.create_template(template)
        
        with pytest.raises(ValueError, match="Missing required variable"):
            manager.render_template("required-test", {})
    
    def test_list_by_category(self, manager):
        """Can list templates by category."""
        # Create some templates
        for i in range(3):
            manager.create_template(Template(
                id=f"spec-{i}",
                name=f"Spec {i}",
                description="",
                category="specification",
                content=""
            ))
        
        for i in range(2):
            manager.create_template(Template(
                id=f"plan-{i}",
                name=f"Plan {i}",
                description="",
                category="plan",
                content=""
            ))
        
        specs = manager.list_templates(category="specification")
        plans = manager.list_templates(category="plan")
        
        spec_names = [t.name for t in specs]
        plan_names = [t.name for t in plans]
        
        assert any("Spec" in n for n in spec_names)
        assert any("Plan" in n for n in plan_names)
    
    def test_update_template(self, manager):
        """Can update existing template."""
        template = Template(
            id="update-test",
            name="Original Name",
            description="Original",
            category="test",
            content="Original content"
        )
        
        manager.create_template(template)
        
        updated = manager.update_template("update-test", name="Updated Name")
        
        assert updated is not None
        assert updated.name == "Updated Name"
    
    def test_delete_template(self, manager):
        """Can delete a template."""
        template = Template(
            id="delete-test",
            name="To Delete",
            description="",
            category="test",
            content=""
        )
        
        manager.create_template(template)
        result = manager.delete_template("delete-test")
        
        assert result is True
        assert manager.get_template("delete-test") is None
    
    def test_cannot_delete_default_template(self, manager):
        """Cannot delete default templates."""
        # Get a default template ID
        default_id = next(iter(DEFAULT_TEMPLATES.keys()))
        
        result = manager.delete_template(default_id)
        
        assert result is False
    
    def test_get_nonexistent_template(self, manager):
        """Getting nonexistent template returns None."""
        result = manager.get_template("nonexistent-template")
        
        assert result is None


class TestTemplateSerialization:
    """Tests for template serialization."""
    
    def test_template_to_dict(self):
        """Template can be converted to dictionary."""
        from datetime import datetime
        
        template = Template(
            id="test",
            name="Test",
            description="Description",
            category="specification",
            content="Content",
            variables={"var": {"type": "string"}},
            metadata={"key": "value"},
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )
        
        data = template.to_dict()
        
        assert data["id"] == "test"
        assert data["name"] == "Test"
        assert data["category"] == "specification"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_template_from_dict(self):
        """Template can be created from dictionary."""
        data = {
            "id": "test",
            "name": "Test",
            "description": "Description",
            "category": "specification",
            "content": "Content",
            "variables": {"var": {"type": "string"}},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        template = Template.from_dict(data)
        
        assert template.id == "test"
        assert template.name == "Test"
        assert template.category == "specification"


class TestTemplateImportExport:
    """Tests for template import/export."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        return TemplateManager(templates_dir=tmp_path / "templates")
    
    def test_export_template_yaml(self, manager, tmp_path):
        """Can export template to YAML."""
        template = Template(
            id="export-test",
            name="Export Test",
            description="Test",
            category="test",
            content="Content"
        )
        
        manager.create_template(template)
        
        output_path = tmp_path / "exported.yaml"
        result = manager.export_template("export-test", output_path)
        
        assert result.exists()
        assert output_path.exists()
    
    def test_export_template_json(self, manager, tmp_path):
        """Can export template to JSON."""
        template = Template(
            id="export-json-test",
            name="Export JSON Test",
            description="Test",
            category="test",
            content="Content"
        )
        
        manager.create_template(template)
        
        output_path = tmp_path / "exported.json"
        result = manager.export_template("export-json-test", output_path)
        
        assert result.exists()
    
    def test_import_template_yaml(self, manager, tmp_path):
        """Can import template from YAML."""
        # Create a YAML file
        yaml_content = """
id: imported-test
name: Imported Test
description: An imported template
category: specification
content: |
  # {title}
  
  {description}
variables:
  title:
    type: string
    required: true
  description:
    type: string
"""
        
        import_path = tmp_path / "import.yaml"
        import_path.write_text(yaml_content)
        
        template = manager.import_template(import_path)
        
        assert template.id == "imported-test"
        assert template.name == "Imported Test"
        assert manager.get_template("imported-test") is not None


class TestDefaultTemplates:
    """Tests for default template functionality."""
    
    def test_default_templates_defined(self):
        """Default templates are defined in module."""
        # Check DEFAULT_TEMPLATES dict
        assert "feature-spec" in DEFAULT_TEMPLATES
        assert "bug-fix" in DEFAULT_TEMPLATES
    
    def test_default_template_structure(self):
        """Default templates have expected structure."""
        feature_spec = DEFAULT_TEMPLATES["feature-spec"]
        
        assert feature_spec["category"] == "specification"
        assert "content" in feature_spec
        assert "variables" in feature_spec
    
    def test_list_default_templates(self, tmp_path):
        """Can list default templates from manager."""
        manager = TemplateManager(templates_dir=tmp_path)
        templates = manager.list_templates()
        
        # Should include default templates
        template_ids = [t.id for t in templates]
        assert "feature-spec" in template_ids
    
    def test_render_feature_spec(self, tmp_path):
        """Can render feature specification template."""
        manager = TemplateManager(templates_dir=tmp_path)
        
        rendered = manager.render_template("feature-spec", {
            "feature_name": "User Authentication",
            "description": "Add user login functionality",
            "user_stories": ["As a user, I can log in"],
            "acceptance_criteria": ["Login form works"],
            "technical_notes": "Use OAuth2"
        })
        
        assert "User Authentication" in rendered
        assert "Add user login functionality" in rendered
    
    def test_render_bug_fix_template(self, tmp_path):
        """Can render bug fix template."""
        manager = TemplateManager(templates_dir=tmp_path)
        
        rendered = manager.render_template("bug-fix", {
            "bug_title": "Login fails",
            "description": "Users cannot log in",
            "steps_to_reproduce": ["Go to login page", "Enter credentials"],
            "expected_behavior": "User should be logged in",
            "actual_behavior": "Error message shown"
        })
        
        assert "Login fails" in rendered
        assert "Users cannot log in" in rendered
