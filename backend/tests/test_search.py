from __future__ import annotations

import pytest


def _db_available() -> bool:
    try:
        from app.db.session import engine
        import sqlalchemy as sa

        with engine.connect() as c:
            c.execute(sa.text("select 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="DB not available")


def test_search_products_ordering():
    from app.search import search_products
    from app.schemas import SearchFilters

    results = search_products(
        query="shirt",
        filters=SearchFilters(category=["men's clothing"], in_stock=True),
        k=5,
    )

    assert isinstance(results, list)
    if len(results) >= 2:
        prev = None
        for _prod, scores in results:
            assert "final" in scores
            if prev is not None:
                assert scores["final"] <= prev + 1e-9
            prev = scores["final"]


