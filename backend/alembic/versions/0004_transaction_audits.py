"""Add private reviews of simulated purchases."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transaction_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column("necessity_rating", sa.Integer(), nullable=False),
        sa.Column("reflection", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("necessity_rating BETWEEN 1 AND 10", name="ck_audit_rating_range"),
    )
    op.create_index("ix_transaction_audits_user_id", "transaction_audits", ["user_id"])


def downgrade():
    op.drop_table("transaction_audits")
