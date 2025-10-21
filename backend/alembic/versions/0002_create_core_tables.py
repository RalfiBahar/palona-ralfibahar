"""create core tables with vector columns and indexes

Revision ID: 0002
Revises: 0001
Create Date: 2025-10-21

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector is installed (no-op if already done)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    op.create_table(
        "product",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("brand", sa.Text(), nullable=True),
        sa.Column("category", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.Text(), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("color", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("material", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("size", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("attributes", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("in_stock", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("text_embedding", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("image_embedding", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("keywords", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "shortlist",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("product_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("product.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Convert float arrays to vector using ALTER (for accurate vector type)
    op.execute("ALTER TABLE product ALTER COLUMN text_embedding TYPE vector(1536);")
    op.execute("ALTER TABLE product ALTER COLUMN image_embedding TYPE vector(512);")

    # Indexes: IVFFlat on vectors and GIN on arrays
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_text_embedding_ivfflat ON product USING ivfflat (text_embedding vector_cosine_ops) WITH (lists = 100);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_image_embedding_ivfflat ON product USING ivfflat (image_embedding vector_cosine_ops) WITH (lists = 100);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_keywords_gin ON product USING GIN (keywords);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_color_gin ON product USING GIN (color);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_material_gin ON product USING GIN (material);")

    # Trigger to auto-update updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trigger_set_updated_at
        BEFORE UPDATE ON product
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_set_updated_at ON product;")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
    op.drop_table("event")
    op.drop_table("shortlist")
    op.drop_table("product")


