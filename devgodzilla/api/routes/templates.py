"""API routes for template management."""

from typing import List, Optional, Any, Dict
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime

# Check if python-multipart is available for file uploads
import importlib.util
MULTIPART_AVAILABLE = importlib.util.find_spec("multipart") is not None

from devgodzilla.api.dependencies import get_service_context, Database
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.template_manager import TemplateManager, Template, get_template_manager

router = APIRouter(prefix="/templates", tags=["templates"])


# Pydantic models for request/response

class TemplateVariableConfig(BaseModel):
    """Configuration for a template variable."""
    type: str = "string"
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None
    description: Optional[str] = None


class TemplateCreate(BaseModel):
    """Request model for creating a template."""
    id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    category: str = Field(default="specification", pattern=r"^(specification|plan|protocol|checklist)$")
    content: str = ""
    variables: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    """Request model for updating a template."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, pattern=r"^(specification|plan|protocol|checklist)$")
    content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    """Response model for a template."""
    id: str
    name: str
    description: str
    category: str
    content: str
    variables: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    is_default: bool = False


class TemplateRender(BaseModel):
    """Request model for rendering a template."""
    variables: Dict[str, Any] = Field(default_factory=dict)


class TemplateRenderResponse(BaseModel):
    """Response model for rendered template."""
    content: str
    template_id: str


class TemplateListResponse(BaseModel):
    """Response model for template list."""
    items: List[TemplateResponse]
    total: int
    categories: List[str]


def get_template_manager_instance(
    ctx: ServiceContext = Depends(get_service_context),
) -> TemplateManager:
    """Get template manager instance."""
    config = ctx.config
    templates_dir = Path(getattr(config, "config_dir", ".")) / "templates"
    return get_template_manager(templates_dir)


def _template_to_response(template: Template, is_default: bool = False) -> TemplateResponse:
    """Convert Template dataclass to response model."""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        content=template.content,
        variables=template.variables,
        metadata=template.metadata,
        created_at=template.created_at.isoformat() if isinstance(template.created_at, datetime) else str(template.created_at),
        updated_at=template.updated_at.isoformat() if isinstance(template.updated_at, datetime) else str(template.updated_at),
        is_default=is_default,
    )


@router.get("", response_model=TemplateListResponse)
def list_templates(
    category: Optional[str] = Query(None, description="Filter by category: specification, plan, protocol, checklist"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """
    List all templates.
    
    Supports filtering by category and text search.
    """
    # Validate category if provided
    valid_categories = ["specification", "plan", "protocol", "checklist"]
    if category and category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )
    
    templates = manager.list_templates(category=category)
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        templates = [
            t for t in templates
            if search_lower in t.name.lower() or search_lower in t.description.lower()
        ]
    
    # Mark default templates
    from devgodzilla.services.template_manager import DEFAULT_TEMPLATES
    items = [
        _template_to_response(t, is_default=(t.id in DEFAULT_TEMPLATES))
        for t in templates
    ]
    
    # Get unique categories
    categories = sorted(set(t.category for t in templates))
    
    return TemplateListResponse(
        items=items,
        total=len(items),
        categories=categories,
    )


@router.get("/categories")
def list_categories(
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """List all available template categories."""
    templates = manager.list_templates()
    categories = sorted(set(t.category for t in templates))
    
    return {
        "categories": categories,
        "counts": {
            cat: len([t for t in templates if t.category == cat])
            for cat in categories
        }
    }


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """Get a template by ID."""
    template = manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    from devgodzilla.services.template_manager import DEFAULT_TEMPLATES
    return _template_to_response(template, is_default=(template_id in DEFAULT_TEMPLATES))


@router.post("", response_model=TemplateResponse, status_code=201)
def create_template(
    template: TemplateCreate,
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """Create a new template."""
    # Check if template already exists
    existing = manager.get_template(template.id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Template already exists: {template.id}"
        )
    
    # Create template
    new_template = Template(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        content=template.content,
        variables=template.variables,
        metadata=template.metadata,
    )
    
    created = manager.create_template(new_template)
    return _template_to_response(created)


@router.patch("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str,
    updates: TemplateUpdate,
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """Update a template."""
    # Build update dict (exclude None values)
    update_dict = updates.model_dump(exclude_unset=True)
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    updated = manager.update_template(template_id, **update_dict)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    from devgodzilla.services.template_manager import DEFAULT_TEMPLATES
    return _template_to_response(updated, is_default=(template_id in DEFAULT_TEMPLATES))


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """Delete a template."""
    # Check if template exists
    template = manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    # Try to delete
    success = manager.delete_template(template_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default template or template deletion failed"
        )
    
    return {"success": True, "message": f"Template {template_id} deleted"}


@router.post("/{template_id}/render", response_model=TemplateRenderResponse)
def render_template(
    template_id: str,
    render: TemplateRender,
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """Render a template with variables."""
    try:
        content = manager.render_template(template_id, render.variables)
        return TemplateRenderResponse(
            content=content,
            template_id=template_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/duplicate", response_model=TemplateResponse, status_code=201)
def duplicate_template(
    template_id: str,
    new_id: str = Query(..., description="ID for the new template"),
    new_name: Optional[str] = Query(None, description="Name for the new template"),
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """Duplicate an existing template with a new ID."""
    # Get source template
    source = manager.get_template(template_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    # Check new ID doesn't exist
    if manager.get_template(new_id):
        raise HTTPException(
            status_code=409,
            detail=f"Template already exists: {new_id}"
        )
    
    # Create duplicate
    duplicate = Template(
        id=new_id,
        name=new_name or f"{source.name} (Copy)",
        description=source.description,
        category=source.category,
        content=source.content,
        variables=source.variables.copy(),
        metadata=source.metadata.copy(),
    )
    
    created = manager.create_template(duplicate)
    return _template_to_response(created)


# Conditionally add import endpoint if multipart support is available
if MULTIPART_AVAILABLE:
    from fastapi import UploadFile, File
    
    @router.post("/import")
    async def import_template(
        file: UploadFile = File(...),
        manager: TemplateManager = Depends(get_template_manager_instance),
    ):
        """Import a template from a YAML or JSON file."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file extension
        suffix = Path(file.filename).suffix.lower()
        if suffix not in [".yaml", ".yml", ".json"]:
            raise HTTPException(
                status_code=400,
                detail="File must be YAML (.yaml, .yml) or JSON (.json)"
            )
        
        # Read file content
        content = await file.read()
        
        # Save to temp file and import
        import tempfile
        with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            template = manager.import_template(tmp_path)
            return {
                "success": True,
                "template": _template_to_response(template),
                "message": f"Template {template.id} imported successfully",
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            tmp_path.unlink(missing_ok=True)


@router.get("/{template_id}/export")
def export_template(
    template_id: str,
    format: str = Query("yaml", description="Export format: yaml or json"),
    manager: TemplateManager = Depends(get_template_manager_instance),
):
    """Export a template to YAML or JSON format."""
    from fastapi.responses import PlainTextResponse
    
    template = manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    if format == "json":
        import json
        content = json.dumps(template.to_dict(), indent=2)
        media_type = "application/json"
        filename = f"{template_id}.json"
    else:
        import yaml
        content = yaml.dump(template.to_dict(), default_flow_style=False, sort_keys=False)
        media_type = "text/yaml"
        filename = f"{template_id}.yaml"
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
