from typing import Optional

from tasksgodzilla.logging import get_logger
from tasksgodzilla.services import OnboardingService
from tasksgodzilla.storage import BaseDatabase

log = get_logger(__name__)


def handle_project_setup(project_id: int, db: BaseDatabase, protocol_run_id: Optional[int] = None) -> None:
    """
    Adapter that delegates project setup to the service layer.
    """
    service = OnboardingService(db=db)
    service.run_project_setup_job(project_id, protocol_run_id=protocol_run_id)

