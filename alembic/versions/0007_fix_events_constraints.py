"""Fix events table constraints for project-level events."""

from alembic import op
import sqlalchemy as sa

revision = "0007_fix_events_constraints"
down_revision = "0006_policy_effective_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True))
        batch_op.alter_column("protocol_run_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_index("idx_events_project", ["project_id", "created_at"])


def downgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_index("idx_events_project")
        batch_op.alter_column("protocol_run_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("project_id")
