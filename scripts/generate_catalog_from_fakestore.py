#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any, Dict, List

import httpx


FAKESTORE_URL = "https://fakestoreapi.com/products"


def _seed_int(key: str) -> int:
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest(), 16) % (2**31)


def _pick(options: List[str], seed: int, n: int = 1) -> List[str]:
    # simple deterministic picks without importing random
    picked: List[str] = []
    m = len(options)
    if m == 0 or n <= 0:
        return picked
    for i in range(n):
        idx = (seed + i * 1315423911) % m
        picked.append(options[idx])
    # de-dup while preserving order
    deduped: List[str] = []
    seen = set()
    for v in picked:
        if v not in seen:
            deduped.append(v)
            seen.add(v)
    return deduped


CATEGORY_BRANDS: Dict[str, List[str]] = {
    "men's clothing": ["Northline", "Seabrook", "Orbit", "PeakForm"],
    "women's clothing": ["Eloise", "Solstice", "Rainier", "CoastalWeave"],
    "jewelery": ["Aurum", "Lustre", "Regalia", "Gemsmith"],
    "electronics": ["Voltix", "Techton", "Auralex", "SkySound"],
}

CATEGORY_COLORS: Dict[str, List[str]] = {
    "men's clothing": ["black", "navy", "gray"],
    "women's clothing": ["ivory", "green", "yellow"],
    "jewelery": ["gold", "silver", "rose gold"],
    "electronics": ["black", "white"],
}

CATEGORY_MATERIALS: Dict[str, List[str]] = {
    "men's clothing": ["cotton", "polyester", "denim"],
    "women's clothing": ["cotton", "silk", "viscose"],
    "jewelery": ["gold", "silver", "stainless steel"],
    "electronics": ["plastic", "aluminum"],
}

CATEGORY_SIZES: Dict[str, List[str]] = {
    "men's clothing": ["S", "M", "L", "XL"],
    "women's clothing": ["XS", "S", "M", "L"],
    "jewelery": ["OS"],
    "electronics": ["OS"],
}


def _derive_gender(category: str) -> str | None:
    c = category.lower()
    if "men" in c:
        return "men"
    if "women" in c:
        return "women"
    return "unisex"


def _keywords_from(title: str, category: str, brand: str | None) -> List[str]:
    words = [w.strip().lower() for w in title.replace("/", " ").split() if w.strip()]
    kw = list(dict.fromkeys(words))  # unique preserve order
    if brand:
        kw.append(brand.lower())
    if category:
        kw.append(category.lower())
    return kw[:12]


def fetch_products() -> List[Dict[str, Any]]:
    with httpx.Client(timeout=10.0) as client:
        r = client.get(FAKESTORE_URL)
        r.raise_for_status()
        return r.json()


def enrich(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for p in products:
        pid = str(p.get("id"))
        title = str(p.get("title", "")).strip()
        category = str(p.get("category", "")).strip()
        desc = str(p.get("description", "")).strip()
        image = str(p.get("image", "")).strip()
        price = float(p.get("price", 0.0))
        rating = (p.get("rating") or {}).get("rate")

        seed = _seed_int(pid + title)
        brand = _pick(CATEGORY_BRANDS.get(category, ["Generic"]), seed, 1)[:1]
        brand_val = brand[0] if brand else "Generic"

        color = _pick(CATEGORY_COLORS.get(category, ["black"]), seed + 11, 2)
        materials = _pick(CATEGORY_MATERIALS.get(category, ["plastic"]), seed + 23, 2)
        sizes = CATEGORY_SIZES.get(category, ["OS"])
        gender = _derive_gender(category)
        keywords = _keywords_from(title, category, brand_val)

        record = {
            "title": title,
            "brand": brand_val,
            "category": [category] if category else [],
            "description": desc,
            "price_cents": int(round(price * 100)),
            "currency": "USD",
            "image_url": image,
            "color": color,
            "material": materials,
            "size": sizes,
            "gender": gender,
            "attributes": {
                "source": "fakestoreapi",
                "fakestore_id": pid,
            },
            "rating": float(rating) if rating is not None else None,
            "url": f"https://fakestoreapi.com/products/{pid}",
            "in_stock": True,
            "keywords": keywords,
        }
        enriched.append(record)
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output path for catalog JSON")
    args = parser.parse_args()

    products = fetch_products()
    data = enrich(products)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(data)} products to {args.out}")


if __name__ == "__main__":
    main()


