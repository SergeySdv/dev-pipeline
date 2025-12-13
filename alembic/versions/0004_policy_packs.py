"""Add policy packs and per-project policy selection."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_policy_packs"
down_revision = "0003_protocol_template_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("pack", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("key", "version", name="uq_policy_packs_key_version"),
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("policy_pack_key", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("policy_pack_version", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("policy_overrides", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("policy_repo_local_enabled", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("policy_effective_hash", sa.Text(), nullable=True))

    with op.batch_alter_table("protocol_runs") as batch_op:
        batch_op.add_column(sa.Column("policy_pack_key", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("policy_pack_version", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("policy_effective_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("protocol_runs") as batch_op:
        batch_op.drop_column("policy_effective_hash")
        batch_op.drop_column("policy_pack_version")
        batch_op.drop_column("policy_pack_key")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("policy_effective_hash")
        batch_op.drop_column("policy_repo_local_enabled")
        batch_op.drop_column("policy_overrides")
        batch_op.drop_column("policy_pack_version")
        batch_op.drop_column("policy_pack_key")

    op.drop_table("policy_packs")

