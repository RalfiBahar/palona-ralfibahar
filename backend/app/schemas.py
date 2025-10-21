from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProductCard(BaseModel):
    id: str
    title: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    price_cents: Optional[int] = None
    currency: str = Field(default="USD")
    in_stock: bool = Field(default=True)
    url: Optional[str] = None
    badges: Optional[list[str]] = None


class ProductDetail(ProductCard):
    category: Optional[list[str]] = None
    description: Optional[str] = None
    color: Optional[list[str]] = None
    material: Optional[list[str]] = None
    size: Optional[list[str]] = None
    gender: Optional[str] = None
    attributes: Optional[dict] = None
    rating: Optional[float] = None
    url: Optional[str] = None
    keywords: Optional[list[str]] = None


class SearchFilters(BaseModel):
    category: Optional[list[str]] = None
    price_min_cents: Optional[int] = None
    price_max_cents: Optional[int] = None
    color: Optional[list[str]] = None
    material: Optional[list[str]] = None
    size: Optional[list[str]] = None
    brand: Optional[list[str]] = None
    gender: Optional[str] = None
    in_stock: Optional[bool] = None


class SearchRequest(BaseModel):
    query: Optional[str] = None
    filters: Optional[SearchFilters] = None
    k: int = Field(default=12, ge=1, le=200)


class RecommendRequest(BaseModel):
    use_case: str
    constraints: Optional[SearchFilters] = None
    k: int = Field(default=12, ge=1, le=200)


class ImageSearchRequest(BaseModel):
    upload_id: str
    k: int = Field(default=12, ge=1, le=200)


class AgentChatRequest(BaseModel):
    message: str
    context: Optional[list[dict]] = None


class AgentChatResponse(BaseModel):
    intent: Literal['chitchat','text_recommendation','image_search','catalog_qna']
    answer: str
    products: Optional[list[ProductCard]] = None
    refinements: Optional[list[str]] = None


