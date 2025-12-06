"""Add template config/source to protocol_runs."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_protocol_template_config"
down_revision = "0002_step_engine_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("protocol_runs") as batch_op:
        batch_op.add_column(sa.Column("template_config", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("template_source", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("protocol_runs") as batch_op:
        batch_op.drop_column("template_source")
        batch_op.drop_column("template_config")
