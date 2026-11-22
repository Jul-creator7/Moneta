"""Add owner-scoped savings goals."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("target_minor", sa.BigInteger(), nullable=False),
        sa.Column("allocated_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("monthly_minor", sa.BigInteger(), nullable=False),
        sa.Column("target_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_minor > 0", name="ck_goal_positive_target"),
        sa.CheckConstraint("allocated_minor >= 0 AND allocated_minor <= target_minor", name="ck_goal_allocation"),
        sa.CheckConstraint("monthly_minor >= 0", name="ck_goal_monthly_nonnegative"),
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])


def downgrade():
    op.drop_table("savings_goals")
