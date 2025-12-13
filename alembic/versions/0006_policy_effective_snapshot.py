"""
Add policy_effective_json snapshot to protocol_runs.
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_policy_effective_snapshot"
down_revision = "0005_policy_enforcement_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("protocol_runs") as batch_op:
        batch_op.add_column(sa.Column("policy_effective_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("protocol_runs") as batch_op:
        batch_op.drop_column("policy_effective_json")

