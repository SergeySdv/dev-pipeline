"""Add spec_runs table for SpecKit workflow tracking."""

from alembic import op
import sqlalchemy as sa

revision = "0008_add_spec_runs"
down_revision = "0007_fix_events_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_spec_runs_project", "spec_runs", ["project_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_spec_runs_project", table_name="spec_runs")
    op.drop_table("spec_runs")
