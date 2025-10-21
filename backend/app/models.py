from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "product"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text), nullable=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    price_cents: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    currency: Mapped[str] = mapped_column(sa.Text, server_default=sa.text("'USD'"), nullable=False)
    image_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    color: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text), nullable=True)
    material: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text), nullable=True)
    size: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text), nullable=True)
    gender: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rating: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    in_stock: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"), nullable=False)
    text_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    image_embedding: Mapped[list[float] | None] = mapped_column(Vector(512), nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.func.now(), nullable=False
    )


class Shortlist(Base):
    __tablename__ = "shortlist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("product.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


class Event(Base):
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(sa.Text, nullable=False)
    kind: Mapped[str] = mapped_column(sa.Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


