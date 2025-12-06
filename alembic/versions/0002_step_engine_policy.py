"""Add engine/policy/runtime_state to step_runs."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_step_engine_policy"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("step_runs") as batch_op:
        batch_op.add_column(sa.Column("engine_id", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("policy", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("runtime_state", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("step_runs") as batch_op:
        batch_op.drop_column("runtime_state")
        batch_op.drop_column("policy")
        batch_op.drop_column("engine_id")
