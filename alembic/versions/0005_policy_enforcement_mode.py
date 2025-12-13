"""Add policy enforcement mode to projects."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_policy_enforcement_mode"
down_revision = "0004_policy_packs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("policy_enforcement_mode", sa.Text(), nullable=True, server_default="warn"))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("policy_enforcement_mode")

