from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
import sqlalchemy as sa

from app.db.session import SessionLocal
from app.models import Product
from app.schemas import ProductDetail


router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> ProductDetail:
    try:
        pid = uuid.UUID(product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid product id")

    with SessionLocal() as session:
        prod = session.execute(sa.select(Product).where(Product.id == pid)).scalar_one_or_none()
        if not prod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")

        return ProductDetail(
            id=str(prod.id),
            title=prod.title,
            brand=prod.brand,
            image_url=prod.image_url,
            price_cents=prod.price_cents,
            currency=prod.currency,
            in_stock=prod.in_stock,
            url=prod.url,
            badges=None,
            category=prod.category,
            description=prod.description,
            color=prod.color,
            material=prod.material,
            size=prod.size,
            gender=prod.gender,
            attributes=prod.attributes,
            rating=prod.rating,
            keywords=prod.keywords,
        )


