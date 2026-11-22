"""Add crowdsourced banknote stories and a simulated deal catalog."""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "banknotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("denomination", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(32), nullable=False),
        sa.Column("series", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("currency", "denomination", "serial_number", "series", name="uq_banknote_identity"),
        sa.CheckConstraint("denomination > 0", name="ck_banknote_positive_denomination"),
    )
    op.create_table(
        "banknote_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("banknote_id", sa.Integer(), sa.ForeignKey("banknotes.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_banknote_event_user_request"),
    )
    op.create_index("ix_banknote_events_banknote_id", "banknote_events", ["banknote_id"])
    deals = op.create_table(
        "deals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store", sa.String(80), nullable=False),
        sa.Column("product", sa.String(100), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("original_minor", sa.Integer(), nullable=False),
        sa.Column("sale_minor", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("expires_on", sa.Date()),
        sa.CheckConstraint("sale_minor >= 0 AND original_minor > sale_minor", name="ck_deal_sale_price"),
    )
    examples = (
        ("Maple Pantry", "Seasonal produce basket", "Food", "Montréal", 2400, 1800, 45.5093, -73.5735),
        ("Cedar Table", "Lunch bowl", "Food", "Montréal", 1600, 1150, 45.4970, -73.5680),
        ("Second Stitch", "Pre-owned denim jacket", "Clothing", "Montréal", 4900, 3200, 45.5315, -73.5858),
        ("North Market", "Pantry staples bundle", "Food", "Laval", 2900, 2200, 45.5709, -73.7384),
        ("River Thread", "Cotton crewneck", "Clothing", "Laval", 3600, 2400, 45.5639, -73.7190),
        ("Harbour Pantry", "Fresh produce box", "Food", "Toronto", 2800, 2050, 43.6536, -79.3925),
        ("Evergreen Rack", "Canvas tote", "Clothing", "Toronto", 2000, 1450, 43.6468, -79.4025),
    )
    fields = ("store", "product", "category", "city", "original_minor", "sale_minor", "latitude", "longitude")
    op.bulk_insert(deals, [dict(zip(fields, example), currency="CAD") for example in examples])


def downgrade():
    op.drop_table("deals")
    op.drop_table("banknote_events")
    op.drop_table("banknotes")
