"""Add optional image attachments to posts and banknote messages."""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("posts", sa.Column("image", sa.Text()))
    op.add_column("banknote_events", sa.Column("image", sa.Text()))


def downgrade():
    for table in ("banknote_events", "posts"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("image")
