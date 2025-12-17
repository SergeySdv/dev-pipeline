"""
Generate Feature Specification Script

Generates a feature specification using AI via SpecificationService.

Args:
    project_id: Project ID
    feature_request: Feature description
    branch_name: Optional branch name

Returns:
    spec_path: Path to generated spec
"""

import os
from pathlib import Path
from datetime import datetime

try:
    from devgodzilla.config import Config
    from devgodzilla.services.base import ServiceContext
    from devgodzilla.db import get_database
    from devgodzilla.services import SpecificationService
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False


def main(
    project_id: int,
    feature_request: str,
    branch_name: str = "",
) -> dict:
    """Generate feature specification."""
    
    if not DEVGODZILLA_AVAILABLE:
        return {"error": "DevGodzilla services not available"}
    
    start_time = datetime.now()
    db = get_database()
    config = Config()
    context = ServiceContext(config=config)
    
    # Get project
    project = db.get_project(project_id)
    if not project or not project.local_path:
        return {"error": f"Project {project_id} not found"}
        
    spec_service = SpecificationService(context, db=db)
    
    # Generate spec
    result = spec_service.run_specify(
        project_path=project.local_path,
        description=feature_request,
        project_id=project_id,
        feature_name=branch_name.replace("feature-", "") if branch_name.startswith("feature-") else None
    )
    
    if not result.success:
        return {"error": result.error}
        
    return {
        "spec_path": result.spec_path,
        "feature_name": result.feature_name,
        "spec_number": result.spec_number,
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
    }
