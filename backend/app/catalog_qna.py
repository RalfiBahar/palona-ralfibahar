from __future__ import annotations

from typing import Any

from app.models import Product


def answer_about_product(query: str, product: Product) -> str:
    """
    Tiny fact retriever: extract only known fields without hallucinating.
    Returns a short paragraph constrained to actual data.
    """
    parts: list[str] = []
    if product.title:
        parts.append(f"Title: {product.title}.")
    if product.brand:
        parts.append(f"Brand: {product.brand}.")
    if product.category:
        parts.append(f"Category: {', '.join(product.category)}.")
    if product.price_cents is not None and product.currency:
        price = f"{product.price_cents/100:.2f} {product.currency}"
        parts.append(f"Price: {price}.")
    if product.color:
        parts.append(f"Colors: {', '.join(product.color)}.")
    if product.material:
        parts.append(f"Materials: {', '.join(product.material)}.")
    if product.size:
        parts.append(f"Sizes: {', '.join(product.size)}.")
    if product.gender:
        parts.append(f"For: {product.gender}.")
    if product.in_stock:
        parts.append("In stock.")
    else:
        parts.append("Out of stock.")
    if product.rating is not None:
        parts.append(f"Rating: {product.rating:.1f}.")
    if product.description:
        parts.append(f"Description: {product.description}")

    if not parts:
        return "No additional details are available for this product."
    return " " .join(parts)


