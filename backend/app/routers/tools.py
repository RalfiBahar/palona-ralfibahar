from __future__ import annotations

import time
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi import status
from loguru import logger
import sqlalchemy as sa

from pydantic import BaseModel

from app.schemas import SearchRequest, ProductCard, RecommendRequest, SearchFilters, ImageSearchRequest
from app.search import search_products
from app.db.session import SessionLocal
from app.models import Event, Product
from app.core.settings import get_settings
from app.embeddings import get_image_embedding
from PIL import Image
from pathlib import Path
from io import BytesIO
from pgvector.sqlalchemy import Vector


router = APIRouter(prefix="/tools", tags=["tools"])
settings = get_settings()


def _badges_for_product(prod) -> list[str]:  # type: ignore[no-untyped-def]
    badges: list[str] = []
    if prod.in_stock:
        badges.append("in_stock")
    if (prod.rating or 0) >= 4.5:
        badges.append("top_rated")
    if (prod.price_cents or 0) <= 2000:
        badges.append("budget")
    return badges


@router.post("/product.search", response_model=List[ProductCard])
def product_search(payload: SearchRequest) -> list[ProductCard]:
    t0 = time.time()
    results = search_products(payload.query, payload.filters, payload.k)
    cards: list[ProductCard] = []
    for prod, scores in results:
        cards.append(
            ProductCard(
                id=str(prod.id),
                title=prod.title,
                brand=prod.brand,
                image_url=prod.image_url,
                price_cents=prod.price_cents,
                currency=prod.currency or "USD",
                in_stock=prod.in_stock,
                url=prod.url,
                badges=_badges_for_product(prod),
            )
        )

    # log event
    duration_ms = int((time.time() - t0) * 1000)
    try:
        with SessionLocal() as session:
            session.add(
                Event(
                    session_id="anon",  # could be from auth/cookies later
                    kind="product.search",
                    payload={
                        "query": payload.query,
                        "filters": payload.filters.model_dump() if payload.filters else None,
                        "k": payload.k,
                        "duration_ms": duration_ms,
                        "results": len(cards),
                    },
                )
            )
            session.commit()
    except Exception as e:
        logger.warning(f"failed to log search event: {e}")

    return cards


def _use_case_keywords(use_case: str, constraints: Optional[SearchFilters]) -> list[str]:
    uc = (use_case or "").lower()
    kw: list[str] = []
    if "run" in uc:
        kw += ["running", "breathable", "lightweight"]
    if "hot" in uc or "summer" in uc:
        kw += ["breathable", "mesh", "lightweight"]
    if "hike" in uc or "trail" in uc:
        kw += ["hiking", "waterproof", "grip", "leather"]
    if "winter" in uc or "cold" in uc:
        kw += ["insulated", "warm", "puffer"]
    if "office" in uc:
        kw += ["casual", "loafers", "comfortable"]
    if constraints and constraints.price_max_cents is not None and constraints.price_max_cents <= 5000:
        kw += ["budget"]
    # dedupe preserve order
    seen = set()
    out: list[str] = []
    for t in kw:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


class RecommendItem(BaseModel):
    product: ProductCard
    reason: str


@router.post("/product.recommend", response_model=List[RecommendItem])
def product_recommend(payload: RecommendRequest) -> list[RecommendItem]:
    # Build a synthetic query
    tokens = _use_case_keywords(payload.use_case, payload.constraints)
    if payload.constraints:
        if payload.constraints.category:
            tokens += payload.constraints.category
        if payload.constraints.brand:
            tokens += payload.constraints.brand
        if payload.constraints.color:
            tokens += payload.constraints.color
        if payload.constraints.material:
            tokens += payload.constraints.material

    synthetic_query = " ".join(tokens) or payload.use_case

    # Gather candidates (k=48 as specified)
    candidates = search_products(synthetic_query, payload.constraints, 48)

    # Rerank with extra boosts tailored to use_case facets
    reranked: list[tuple[float, Product, dict, list[str]]] = []
    for prod, scores in candidates:
        boost = 0.0
        reasons: list[str] = []

        # brand boost
        if payload.constraints and payload.constraints.brand and prod.brand in (payload.constraints.brand or []):
            boost += 0.15
            reasons.append(f"brand match: {prod.brand}")

        # category overlap
        if payload.constraints and payload.constraints.category and prod.category:
            if set(prod.category).intersection(set(payload.constraints.category)):
                boost += 0.10
                reasons.append("category match")

        # color/material
        if payload.constraints and payload.constraints.color and prod.color:
            if set(map(str.lower, prod.color)).intersection(set(map(str.lower, payload.constraints.color))):
                boost += 0.05
                reasons.append("color match")
        if payload.constraints and payload.constraints.material and prod.material:
            if set(map(str.lower, prod.material)).intersection(set(map(str.lower, payload.constraints.material))):
                boost += 0.05
                reasons.append("material match")

        # price fit
        if payload.constraints and payload.constraints.price_max_cents is not None and prod.price_cents is not None:
            if prod.price_cents <= payload.constraints.price_max_cents:
                boost += 0.10
                reasons.append("within budget")
            elif prod.price_cents <= int(payload.constraints.price_max_cents * 1.2):
                boost += 0.05
                reasons.append("near budget")

        # use-case keyword presence in product keywords
        if prod.keywords:
            if set(map(str.lower, prod.keywords)).intersection(set(map(str.lower, tokens))):
                boost += 0.10
                reasons.append("use-case keywords")

        final = scores["final"] + boost
        reranked.append((final, prod, scores, reasons))

    reranked.sort(key=lambda x: x[0], reverse=True)
    top = reranked[:6]

    items: list[RecommendItem] = []
    for _, prod, _, reasons in top:
        reason = "; ".join(reasons) if reasons else "best overall fit"
        items.append(
            RecommendItem(
                product=ProductCard(
                    id=str(prod.id),
                    title=prod.title,
                    brand=prod.brand,
                    image_url=prod.image_url,
                    price_cents=prod.price_cents,
                    currency=prod.currency or "USD",
                    in_stock=prod.in_stock,
                    url=prod.url,
                    badges=_badges_for_product(prod),
                ),
                reason=reason,
            )
        )

    return items


# ---------------------------- Uploads and Image Search ----------------------------

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


def _dominant_colors(image: Image.Image, top_k: int = 2) -> list[str]:
    img = image.convert("RGB").resize((64, 64))
    # count exact RGB colors on a small image to avoid palette index issues
    counts = img.getcolors(maxcolors=64 * 64) or []
    counts.sort(reverse=True, key=lambda x: x[0])

    def _name(r: int, g: int, b: int) -> str:
        if r > 220 and g > 220 and b > 220:
            return "white"
        if r < 40 and g < 40 and b < 40:
            return "black"
        if r > g and r > b:
            if g > b and r - g < 40:
                return "orange"
            return "red"
        if g > r and g > b:
            return "green"
        if b > r and b > g:
            return "blue"
        if r > 200 and g > 200:
            return "yellow"
        if r > 150 and b > 150:
            return "magenta"
        if g > 150 and b > 150:
            return "cyan"
        return "gray"

    names: list[str] = []
    for _, (r, g, b) in counts[:top_k * 2]:
        names.append(_name(int(r), int(g), int(b)))

    # dedupe preserve order and limit to top_k
    out: list[str] = []
    seen = set()
    for n in names:
        if n not in seen:
            out.append(n)
            seen.add(n)
        if len(out) >= top_k:
            break
    return out


@router.post("/uploads", tags=["uploads"])
async def upload_image(file: UploadFile = File(...)) -> dict:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 5MB)")

    try:
        img = Image.open(BytesIO(data))
        img = img.convert("RGB")  # strip alpha/exif
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    import uuid as _uuid

    upload_id = f"{_uuid.uuid4().hex}{ext}"
    out_path = upload_dir / upload_id
    img.save(out_path, format="JPEG", quality=90, optimize=True)

    return {"upload_id": upload_id, "url": f"/uploads/{upload_id}"}


@router.post("/image.search", response_model=List[ProductCard])
def image_search(payload: ImageSearchRequest) -> list[ProductCard]:
    # load image
    upload_path = Path(settings.upload_dir) / payload.upload_id
    if not upload_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="upload not found")

    img = Image.open(upload_path).convert("RGB")
    query_vec = get_image_embedding(img)

    # First try KNN on image_embedding if catalog populated
    with SessionLocal() as session:
        vec_param = sa.bindparam("vec", value=query_vec)
        emb = sa.cast(vec_param, Vector(512))
        # Ensure we filter to non-null image_embedding
        distance = Product.image_embedding.op("<=>")(emb)
        stmt = (
            sa.select(Product, (1.0 - distance).label("semantic"))
            .where(Product.image_embedding.isnot(None))
            .order_by(distance.asc())
            .limit(max(payload.k or 12, 8))
        )
        try:
            rows = session.execute(stmt, {"vec": query_vec}).all()
        except Exception as e:
            logger.warning(f"image KNN query failed, falling back to text: {e}")
            rows = []

    if not rows:
        # Fallback: simple caption from colors and search via text
        colors = _dominant_colors(img)
        synthetic = "photo product " + " ".join(colors)
        from app.schemas import SearchFilters, SearchRequest
        results = search_products(synthetic, SearchFilters(), payload.k or 12)
        rows = [(p, s["semantic"]) for p, s in results]

    cards: list[ProductCard] = []
    for prod, _score in rows[: max(payload.k or 12, 8)]:
        cards.append(
            ProductCard(
                id=str(prod.id),
                title=prod.title,
                brand=prod.brand,
                image_url=prod.image_url,
                price_cents=prod.price_cents,
                currency=prod.currency or "USD",
                in_stock=prod.in_stock,
                url=prod.url,
                badges=_badges_for_product(prod),
            )
        )

    # log event
    try:
        with SessionLocal() as session:
            session.add(
                Event(
                    session_id="anon",
                    kind="image.search",
                    payload={"upload_id": payload.upload_id, "results": len(cards)},
                )
            )
            session.commit()
    except Exception as e:
        logger.warning(f"failed to log image search: {e}")

    return cards

