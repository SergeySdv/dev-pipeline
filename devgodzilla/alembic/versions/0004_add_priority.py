"""Add priority column to step_runs

Revision ID: 0004_add_priority
Revises: 0003_agent_assignments
Create Date: 2025-02-22 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0004_add_priority"
down_revision = "0003_agent_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add priority column to step_runs table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Check if column already exists
    columns = [col["name"] for col in inspector.get_columns("step_runs")]
    
    if "priority" not in columns:
        op.add_column(
            "step_runs",
            sa.Column(
                "priority",
                sa.Integer(),
                nullable=True,
                server_default=sa.text("0"),
            ),
        )


def downgrade() -> None:
    """Remove priority column from step_runs table."""
    try:
        op.drop_column("step_runs", "priority")
    except Exception:
        pass
