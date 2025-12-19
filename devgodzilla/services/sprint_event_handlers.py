"""
Sprint Event Handlers

Registers event handlers to update sprint tasks based on protocol execution events.
"""

from devgodzilla.services.events import get_event_bus, StepCompleted, StepFailed
from devgodzilla.services.sprint_integration import SprintIntegrationService
from devgodzilla.cli.main import get_db
from devgodzilla.logging import get_logger

logger = get_logger(__name__)

def register_sprint_event_handlers():
    """Register sprint-related event handlers on the global event bus."""
    bus = get_event_bus()
    
    async def on_step_completed(event: StepCompleted):
        """Update linked task when step completes."""
        try:
            # We need a new DB connection for this async handler context
            db = get_db() 
            service = SprintIntegrationService(db)
            
            # Since update_task_from_step is async, we await it
            updated_task = await service.update_task_from_step(
                step_run_id=event.step_run_id,
                step_status="completed",
            )
            
            if updated_task:
                logger.info(
                    f"Updated task {updated_task.id} status to 'done' from step {event.step_run_id}",
                    extra={
                        "task_id": updated_task.id,
                        "step_run_id": event.step_run_id,
                        "sprint_id": updated_task.sprint_id
                    }
                )
        except Exception as e:
            logger.error(
                f"Failed to update task from step completion event: {e}", 
                extra={"step_run_id": event.step_run_id, "error": str(e)}
            )
    
    async def on_step_failed(event: StepFailed):
        """Update linked task when step fails."""
        try:
            db = get_db()
            service = SprintIntegrationService(db)
            
            updated_task = await service.update_task_from_step(
                step_run_id=event.step_run_id,
                step_status="failed",
            )
            
            if updated_task:
                logger.info(
                    f"Updated task {updated_task.id} status to 'blocked' from step failure {event.step_run_id}",
                    extra={
                        "task_id": updated_task.id,
                        "step_run_id": event.step_run_id
                    }
                )
        except Exception as e:
            logger.error(
                f"Failed to update task from step failure event: {e}",
                extra={"step_run_id": event.step_run_id, "error": str(e)}
            )
    
    # Register handlers
    bus.add_async_handler(StepCompleted, on_step_completed)
    bus.add_async_handler(StepFailed, on_step_failed)
    
    logger.info("Registered sprint integration event handlers")
