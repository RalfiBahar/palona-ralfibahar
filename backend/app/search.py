from __future__ import annotations

from typing import Iterable, Optional, Tuple

import sqlalchemy as sa

from app.db.session import SessionLocal
from app.embeddings import get_text_embedding
from app.models import Product
from app.schemas import SearchFilters
from pgvector.sqlalchemy import Vector


def _tokenize(text: str) -> list[str]:
    # ultra-light tokenizer: lowercase, split on non-alnum, drop empties
    out: list[str] = []
    buff: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            buff.append(ch)
        else:
            if buff:
                out.append("".join(buff))
                buff.clear()
    if buff:
        out.append("".join(buff))
    return out


def _keyword_overlap(tokens: set[str], keywords: Optional[list[str]]) -> float:
    if not tokens or not keywords:
        return 0.0
    keyset = {k.lower() for k in keywords if k}
    inter = tokens.intersection(keyset)
    return 0.0 if not tokens else len(inter) / max(1, len(tokens))


def _rule_bonus(tokens: set[str], p: Product, filters: SearchFilters | None) -> float:
    bonus = 0.0
    # budget fit
    if filters and filters.price_max_cents is not None and p.price_cents is not None:
        if p.price_cents <= filters.price_max_cents:
            bonus += 0.5
    # breathable -> polyester/mesh
    if "breathable" in tokens and (p.material or p.category):
        mats = {m.lower() for m in (p.material or [])}
        if {"polyester", "mesh"}.intersection(mats):
            bonus += 0.25
    # leather preference
    if "leather" in tokens and (p.material):
        mats = {m.lower() for m in (p.material or [])}
        if "leather" in mats:
            bonus += 0.25
    # waterproof preference
    if "waterproof" in tokens:
        mats = {m.lower() for m in (p.material or [])}
        attrs = p.attributes or {}
        if attrs.get("waterproof") is True or {"nylon", "leather"}.intersection(mats):
            bonus += 0.25
    return max(0.0, min(1.0, bonus))


def _apply_sql_filters(stmt, f: SearchFilters | None):  # type: ignore[no-untyped-def]
    if f is None:
        return stmt
    if f.category:
        stmt = stmt.where(Product.category.op("&&")(sa.literal(f.category)))
    if f.price_min_cents is not None:
        stmt = stmt.where(Product.price_cents >= f.price_min_cents)
    if f.price_max_cents is not None:
        stmt = stmt.where(Product.price_cents <= f.price_max_cents)
    if f.size:
        stmt = stmt.where(Product.size.op("&&")(sa.literal(f.size)))
    if f.brand:
        stmt = stmt.where(Product.brand.in_(f.brand))
    if f.gender:
        stmt = stmt.where(Product.gender == f.gender)
    if f.in_stock is not None:
        stmt = stmt.where(Product.in_stock == f.in_stock)
    # optional color/material
    if f.color:
        stmt = stmt.where(Product.color.op("&&")(sa.literal(f.color)))
    if f.material:
        stmt = stmt.where(Product.material.op("&&")(sa.literal(f.material)))
    return stmt


def search_products(query: Optional[str], filters: Optional[SearchFilters], k: int) -> list[tuple[Product, dict]]:
    """
    Returns list of (Product, scores) where scores has {semantic, keyword, rule, final}.
    """
    tokens: set[str] = set(_tokenize(query)) if query else set()
    embedding: Optional[list[float]] = get_text_embedding(query) if query else None

    limit_candidates = max(k, 1) * (5 if query else 2)

    with SessionLocal() as session:
        if embedding is not None:
            emb = sa.literal(embedding).cast(Vector(1536))
            distance_expr = Product.text_embedding.op("<=>")(emb)
            semantic_expr = sa.literal(1.0) - sa.func.coalesce(distance_expr, sa.literal(1.0))
            stmt = sa.select(Product, semantic_expr.label("semantic")).where(sa.true())
            stmt = _apply_sql_filters(stmt, filters)
            stmt = stmt.order_by(distance_expr.asc()).limit(limit_candidates)
        else:
            # No query: rely on filters, return recent/rated items
            semantic_expr = sa.literal(0.0)
            stmt = sa.select(Product, semantic_expr.label("semantic"))
            stmt = _apply_sql_filters(stmt, filters)
            stmt = stmt.order_by(Product.updated_at.desc(), Product.rating.desc().nullslast()).limit(limit_candidates)

        rows = session.execute(stmt).all()

    results: list[tuple[Product, dict]] = []
    for prod, semantic_score in rows:
        kw_score = _keyword_overlap(tokens, prod.keywords)
        rule = _rule_bonus(tokens, prod, filters)
        final = 0.65 * float(semantic_score) + 0.25 * kw_score + 0.10 * rule
        results.append((prod, {"semantic": float(semantic_score), "keyword": kw_score, "rule": rule, "final": final}))

    results.sort(key=lambda x: x[1]["final"], reverse=True)
    return results[:k]


