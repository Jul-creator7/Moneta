"""Add the simulated transaction ledger and provision existing users."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("transaction_type", sa.String(24), nullable=False),
        sa.Column("merchant_name", sa.String(80)),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("transfer_group_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "operation_id", name="uq_transaction_account_operation"),
        sa.CheckConstraint("amount_minor != 0", name="ck_transaction_nonzero"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    users = sa.table("users", sa.column("id"))
    accounts = sa.table(
        "bank_accounts",
        sa.column("user_id"),
        sa.column("account_type"),
        sa.column("name"),
        sa.column("currency"),
    )
    for kind, name in (("chequing", "Chequing"), ("savings", "Savings")):
        exists = sa.select(accounts.c.user_id).where(
            accounts.c.user_id == users.c.id,
            accounts.c.account_type == kind,
            accounts.c.currency == "CAD",
        ).exists()
        op.execute(accounts.insert().from_select(
            ["user_id", "account_type", "name", "currency"],
            sa.select(users.c.id, sa.literal(kind), sa.literal(name), sa.literal("CAD")).where(~exists),
        ))


def downgrade():
    op.drop_table("transactions")
    # Reconcile balances to the Phase 0 baseline when removing the ledger.
    accounts = sa.table("bank_accounts", sa.column("balance_minor"))
    op.execute(accounts.update().values(balance_minor=0))
