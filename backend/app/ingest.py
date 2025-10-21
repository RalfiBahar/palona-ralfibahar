from __future__ import annotations

import argparse
import csv
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import sqlalchemy as sa
from loguru import logger
import httpx

from app.core.settings import get_settings
from app.db.session import engine, SessionLocal
from app.embeddings import get_text_embedding, get_image_embedding
from app.models import Product
from PIL import Image
from io import BytesIO


@dataclass
class CatalogItem:
    title: Optional[str]
    brand: Optional[str]
    category: Optional[list[str]]
    description: Optional[str]
    price_cents: Optional[int]
    currency: Optional[str]
    image_url: Optional[str]
    color: Optional[list[str]]
    material: Optional[list[str]]
    size: Optional[list[str]]
    gender: Optional[str]
    attributes: Optional[dict]
    rating: Optional[float]
    url: Optional[str]
    in_stock: Optional[bool]
    keywords: Optional[list[str]]


def load_json(path: Path) -> list[CatalogItem]:
    data = json.loads(path.read_text())
    items: list[CatalogItem] = []
    for row in data:
        items.append(CatalogItem(**row))
    return items


def load_csv(path: Path) -> list[CatalogItem]:
    items: list[CatalogItem] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # parse list-like fields if present as CSV
            def parse_list(val: Optional[str]) -> Optional[list[str]]:
                if not val:
                    return None
                return [p.strip() for p in val.split("|") if p.strip()]

            items.append(
                CatalogItem(
                    title=row.get("title") or None,
                    brand=row.get("brand") or None,
                    category=parse_list(row.get("category")),
                    description=row.get("description") or None,
                    price_cents=int(row["price_cents"]) if row.get("price_cents") else None,
                    currency=row.get("currency") or None,
                    image_url=row.get("image_url") or None,
                    color=parse_list(row.get("color")),
                    material=parse_list(row.get("material")),
                    size=parse_list(row.get("size")),
                    gender=row.get("gender") or None,
                    attributes=json.loads(row["attributes"]) if row.get("attributes") else None,
                    rating=float(row["rating"]) if row.get("rating") else None,
                    url=row.get("url") or None,
                    in_stock=row.get("in_stock") in ("1", "true", "True"),
                    keywords=parse_list(row.get("keywords")),
                )
            )
    return items


def synthesize_search_text(item: CatalogItem) -> str:
    parts: list[str] = []
    for v in [item.title, item.description, item.brand, ", ".join(item.category or [])]:
        if v:
            parts.append(str(v))
    if item.keywords:
        parts.append(",".join(item.keywords))
    return ". ".join(parts)


def batch(iterable: Iterable[CatalogItem], n: int) -> Iterable[list[CatalogItem]]:
    chunk: list[CatalogItem] = []
    for x in iterable:
        chunk.append(x)
        if len(chunk) >= n:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def upsert_products(items: list[CatalogItem], with_images: bool) -> tuple[int, int]:
    inserted = 0
    updated = 0
    with SessionLocal() as session:
        for itm in items:
            search_text = synthesize_search_text(itm)
            text_vec = get_text_embedding(search_text)

            image_vec: Optional[list[float]] = None
            if with_images and itm.image_url:
                try:
                    with httpx.Client(timeout=10.0) as client:
                        r = client.get(itm.image_url)
                        r.raise_for_status()
                        img = Image.open(BytesIO(r.content))
                        image_vec = get_image_embedding(img)
                except Exception as e:
                    logger.warning(f"image embed failed for {itm.image_url}: {e}")

            # upsert by (brand,title,url) heuristic; fallback create
            existing = session.execute(
                sa.select(Product).where(
                    sa.func.coalesce(Product.brand, "") == (itm.brand or ""),
                    sa.func.coalesce(Product.title, "") == (itm.title or ""),
                    sa.func.coalesce(Product.url, "") == (itm.url or ""),
                )
            ).scalar_one_or_none()

            if existing:
                updated += 1
                existing.title = itm.title
                existing.brand = itm.brand
                existing.category = itm.category
                existing.description = itm.description
                existing.price_cents = itm.price_cents
                existing.currency = (itm.currency or "USD")
                existing.image_url = itm.image_url
                existing.color = itm.color
                existing.material = itm.material
                existing.size = itm.size
                existing.gender = itm.gender
                existing.attributes = itm.attributes
                existing.rating = itm.rating
                existing.url = itm.url
                existing.in_stock = True if itm.in_stock is None else itm.in_stock
                existing.text_embedding = text_vec
                if image_vec is not None:
                    existing.image_embedding = image_vec
            else:
                inserted += 1
                session.add(
                    Product(
                        id=uuid.uuid4(),
                        title=itm.title,
                        brand=itm.brand,
                        category=itm.category,
                        description=itm.description,
                        price_cents=itm.price_cents,
                        currency=(itm.currency or "USD"),
                        image_url=itm.image_url,
                        color=itm.color,
                        material=itm.material,
                        size=itm.size,
                        gender=itm.gender,
                        attributes=itm.attributes,
                        rating=itm.rating,
                        url=itm.url,
                        in_stock=True if itm.in_stock is None else itm.in_stock,
                        text_embedding=text_vec,
                        image_embedding=image_vec,
                        keywords=itm.keywords,
                    )
                )

        session.commit()
    return inserted, updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--with-images", default="false")
    args = parser.parse_args()

    path = Path(args.path)
    with_images = str(args.with_images).lower() in ("1", "true", "yes")

    t0 = time.time()
    if path.suffix.lower() == ".json":
        items = load_json(path)
    elif path.suffix.lower() == ".csv":
        items = load_csv(path)
    else:
        raise SystemExit("Unsupported file type; use .json or .csv")
    t_load = time.time()

    inserted, updated = upsert_products(items, with_images)
    t_ingest = time.time()

    logger.info(f"Loaded {len(items)} items in {t_load - t0:.2f}s")
    logger.info(f"Upserted: inserted={inserted}, updated={updated} in {t_ingest - t_load:.2f}s")
    logger.info(f"Total time: {t_ingest - t0:.2f}s")


if __name__ == "__main__":
    main()


