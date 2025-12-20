"""Add spec_runs table

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01 00:00:01.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    timestamp_type = sa.DateTime() if is_sqlite else sa.TIMESTAMP()

    op.create_table(
        "spec_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("spec_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("base_branch", sa.Text(), nullable=False),
        sa.Column("branch_name", sa.Text(), nullable=True),
        sa.Column("worktree_path", sa.Text(), nullable=True),
        sa.Column("spec_root", sa.Text(), nullable=True),
        sa.Column("spec_number", sa.Integer(), nullable=True),
        sa.Column("feature_name", sa.Text(), nullable=True),
        sa.Column("spec_path", sa.Text(), nullable=True),
        sa.Column("plan_path", sa.Text(), nullable=True),
        sa.Column("tasks_path", sa.Text(), nullable=True),
        sa.Column("checklist_path", sa.Text(), nullable=True),
        sa.Column("analysis_path", sa.Text(), nullable=True),
        sa.Column("implement_path", sa.Text(), nullable=True),
        sa.Column("protocol_run_id", sa.Integer(), sa.ForeignKey("protocol_runs.id"), nullable=True),
        sa.Column("created_at", timestamp_type, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_type, server_default=sa.func.now()),
    )
    op.create_index("idx_spec_runs_project", "spec_runs", ["project_id", "created_at"])

    try:
        op.add_column("events", sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True))
    except Exception:
        pass

    op.alter_column("events", "protocol_run_id", existing_type=sa.Integer(), nullable=True)

    try:
        op.create_index("idx_events_project", "events", ["project_id", "created_at"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index("idx_events_project", table_name="events")
    except Exception:
        pass

    op.alter_column("events", "protocol_run_id", existing_type=sa.Integer(), nullable=False)

    try:
        op.drop_column("events", "project_id")
    except Exception:
        pass

    op.drop_index("idx_spec_runs_project", table_name="spec_runs")
    op.drop_table("spec_runs")
