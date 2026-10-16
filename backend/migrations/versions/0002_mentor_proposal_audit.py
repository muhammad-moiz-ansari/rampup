"""Preserve rejected proposals in mentor-only audit."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "mentor_decisions",
        sa.Column("proposal_snapshot", sa.Text(), nullable=False, server_default=""),
    )


def downgrade():
    op.drop_column("mentor_decisions", "proposal_snapshot")
