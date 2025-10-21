from __future__ import annotations

import json
import re
import uuid
from typing import Literal, Optional

import sqlalchemy as sa
from loguru import logger

from app.core.settings import get_settings
from app.db.session import SessionLocal
from app.models import Product
from app.search import search_products
from app.schemas import (
    AgentChatResponse,
    ProductCard,
    SearchFilters,
    ImageSearchRequest,
)
from app.catalog_qna import answer_about_product


Intent = Literal['chitchat','text_recommendation','image_search','catalog_qna']


def detect_intent(message: str) -> Intent:
    msg = (message or "").strip()
    if not msg:
        return 'chitchat'

    # Heuristic fallback first for speed
    if re.search(r"image:\s*\S+", msg, flags=re.IGNORECASE):
        return 'image_search'
    if re.search(r"\b(recommend|suggest|find|search|show|browse|shopping|shop|see)\b", msg, flags=re.IGNORECASE):
        return 'text_recommendation'
    if re.search(r"\b(details|about|specs?|tell me|what is)\b", msg, flags=re.IGNORECASE):
        return 'catalog_qna'

    # Attempt light OpenAI call for better routing
    try:
        from openai import OpenAI  # lazy import

        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else OpenAI()
        system = (
            "You are an intent router. Respond ONLY with JSON: {\"intent\": one of "
            "['chitchat','text_recommendation','image_search','catalog_qna'] }."
        )
        user = f"Message: {msg}\nClassify intent."
        # Using responses API-style fallback to chat.completions if unavailable
        try:
            resp = client.chat.completions.create(
                model=settings.chat_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
            )
            content = resp.choices[0].message.content
        except Exception:
            # Fallback to responses if needed
            resp = client.responses.create(
                model=settings.chat_model,
                input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0,
            )
            content = resp.output_text
        data = json.loads(content)
        intent = data.get("intent")
        if intent in ('chitchat','text_recommendation','image_search','catalog_qna'):
            return intent  # type: ignore[return-value]
    except Exception as e:
        logger.debug(f"intent openai fallback used: {e}")

    # Final fallback
    return 'chitchat'


def _parse_facets(message: str) -> tuple[str, SearchFilters]:
    text = message.lower()
    # Budget
    budget = None
    m = re.search(r"\$(\d{2,5})|under\s*\$?(\d{2,5})|<(\d{2,5})", text)
    if m:
        for g in m.groups():
            if g:
                try:
                    budget = int(g) * (100 if int(g) < 1000 else 1)  # $99 -> 9900, 12000 cents ok
                except Exception:
                    pass
                break

    # Sizes (simple tokens)
    sizes = [s for s in re.findall(r"\b(xs|s|m|l|xl|xxl|xxxl|\d{1,2})\b", text)] or None

    # Categories (map a few common words)
    cat_map = {
        "shoe": "Shoes",
        "shoes": "Shoes",
        "jacket": "Jackets",
        "dress": "Dresses",
        "shirt": "Shirts",
        "top": "Tops",
        "pants": "Pants",
        "bag": "Bags",
        "jewelry": "jewelery",
        "jewelery": "jewelery",
        "electronics": "electronics",
        "men": "men's clothing",
        "women": "women's clothing",
    }
    cats = []
    for k, v in cat_map.items():
        if re.search(rf"\b{k}\b", text):
            cats.append(v)
    categories = list(dict.fromkeys(cats)) or None

    filters = SearchFilters(
        price_max_cents=budget,
        size=sizes,
        category=categories,
        in_stock=True,
    )
    return message, filters


def _cards_from_products(results) -> list[ProductCard]:  # type: ignore[no-untyped-def]
    cards: list[ProductCard] = []
    for prod, _scores in results:
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
                badges=None,
            )
        )
    return cards


def _openai_client():  # lazy import and safe init
    try:
        from openai import OpenAI
        settings = get_settings()
        return OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else OpenAI()
    except Exception as e:
        logger.debug(f"openai client init failed: {e}")
        return None


def _messages_with_context(context: Optional[list[dict]], message: str) -> list[dict]:
    msgs: list[dict] = []
    if context:
        for m in context[-10:]:  # last 10 turns for brevity
            role = str(m.get("role", "user")).lower()
            content = str(m.get("content", ""))
            if role in {"user", "assistant"} and content:
                msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": message})
    return msgs


def _llm_route_and_extract(message: str, context: Optional[list[dict]]) -> Optional[dict]:
    client = _openai_client()
    if client is None:
        return None
    settings = get_settings()
    system = (
        "You are a helpful shopping assistant and intent router. "
        "Given the conversation and the latest user message, decide the primary intent "
        "('chitchat','text_recommendation','image_search','catalog_qna'). "
        "Also extract a normalized search query and lightweight filters when relevant. "
        "Output ONLY compact JSON with keys: intent, query, filters, refinements. "
        "filters may include: price_max_cents (int), size (list[str]), category (list[str]), "
        "brand (list[str]), gender (str). refinements is a list of up to 5 short suggestions."
    )
    user = (
        "Return JSON. If intent is image_search but no upload id like 'image:<id>' is present, do not invent one. "
        "Example: {\"intent\":\"text_recommendation\",\"query\":\"running shoes\",\"filters\":{\"price_max_cents\":10000,\"size\":[\"10\"]},\"refinements\":[\"under $50\"]}"
    )
    msgs = [
        {"role": "system", "content": system},
    ]
    msgs.extend(_messages_with_context(context, message))
    msgs.append({"role": "system", "content": user})
    try:
        try:
            resp = client.chat.completions.create(
                model=settings.chat_model,
                messages=msgs,
                temperature=0,
            )
            content = resp.choices[0].message.content
        except Exception:
            resp = client.responses.create(
                model=settings.chat_model,
                input=msgs,
                temperature=0,
            )
            content = resp.output_text
        data = json.loads(content or "{}")
        if isinstance(data, dict) and data.get("intent") in ('chitchat','text_recommendation','image_search','catalog_qna'):
            return data
    except Exception as e:
        logger.debug(f"llm route extract failed: {e}")
    return None


def _filters_from_dict(d: Optional[dict]) -> Optional[SearchFilters]:
    if not isinstance(d, dict):
        return None
    try:
        return SearchFilters(
            category=d.get("category"),
            price_min_cents=d.get("price_min_cents"),
            price_max_cents=d.get("price_max_cents"),
            color=d.get("color"),
            material=d.get("material"),
            size=d.get("size"),
            brand=d.get("brand"),
            gender=d.get("gender"),
            in_stock=d.get("in_stock"),
        )
    except Exception:
        return None


def _natural_reply_for_results(message: str, context: Optional[list[dict]], intent: Intent, products: list[ProductCard] | None, refinements: list[str] | None) -> str:
    client = _openai_client()
    if client is None:
        # simple fallback
        if intent == 'text_recommendation':
            return "Here are some picks based on your request:"
        if intent == 'catalog_qna':
            return "Here are the details:"
        if intent == 'image_search':
            return "Closest visual matches:"
        return "Hi! How can I help you today?"
    settings = get_settings()
    system = (
        "You are a warm, concise shopping assistant. "
        "Write a single friendly paragraph responding to the user's last message, "
        "referencing the provided products (by category or general traits, not IDs) if any, "
        "and optionally propose one next step. Keep it under 2 sentences."
    )
    info: list[str] = []
    if products:
        # provide lightweight context to LLM
        for p in products[:6]:
            title = p.title or ""
            brand = p.brand or ""
            info.append(f"- {brand} {title}".strip())
    context_msgs = _messages_with_context(context, message)
    context_msgs.insert(0, {"role": "system", "content": system})
    if info:
        context_msgs.append({"role": "system", "content": "Products:\n" + "\n".join(info)})
    try:
        try:
            resp = client.chat.completions.create(
                model=settings.chat_model,
                messages=context_msgs,
                temperature=0.4,
            )
            return resp.choices[0].message.content or "Here are some options."
        except Exception:
            resp = client.responses.create(
                model=settings.chat_model,
                input=context_msgs,
                temperature=0.4,
            )
            return resp.output_text or "Here are some options."
    except Exception as e:
        logger.debug(f"natural reply llm failed: {e}")
        if intent == 'text_recommendation':
            return "Here are some picks based on your request:"
        if intent == 'catalog_qna':
            return "Here are the details:"
        if intent == 'image_search':
            return "Closest visual matches:"
        return "Happy to help!"


def _rewrite_factual_answer(prompt: str, facts: str) -> str:
    client = _openai_client()
    if client is None:
        return facts
    settings = get_settings()
    system = (
        "You rewrite product facts into a natural, friendly, concise answer. "
        "You MUST only use the provided facts; do not add any information. "
        "Keep to 2 sentences maximum."
    )
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"User question: {prompt}\nFacts to use strictly:\n{facts}"},
    ]
    try:
        try:
            resp = client.chat.completions.create(
                model=settings.chat_model,
                messages=msgs,
                temperature=0.2,
            )
            return resp.choices[0].message.content or facts
        except Exception:
            resp = client.responses.create(
                model=settings.chat_model,
                input=msgs,
                temperature=0.2,
            )
            return resp.output_text or facts
    except Exception as e:
        logger.debug(f"rewrite factual answer failed: {e}")
        return facts


def generate_answer(message: str, context: Optional[list[dict]] = None) -> AgentChatResponse:
    # First, try LLM planning to determine intent and filters
    plan = _llm_route_and_extract(message, context)
    if plan:
        intent = plan.get("intent") or 'chitchat'
    else:
        intent = detect_intent(message)

    if intent == 'chitchat':
        answer = _natural_reply_for_results(message, context, intent, None, ["recommendations", "image search", "product details"])  # type: ignore[arg-type]
        chips = plan.get("refinements") if isinstance(plan, dict) else None
        if not chips:
            chips = ["recommendations", "image search", "product details"]
        return AgentChatResponse(intent=intent, answer=answer, products=None, refinements=chips)

    if intent == 'text_recommendation':
        # Prefer LLM-extracted query/filters; fall back to heuristic
        llm_query = (plan.get("query") if isinstance(plan, dict) else None) or message
        llm_filters = _filters_from_dict(plan.get("filters") if isinstance(plan, dict) else None)
        if llm_filters is None:
            llm_query, llm_filters = _parse_facets(llm_query)
        query, filters = llm_query, llm_filters
        results = search_products(query, filters, 12)
        cards = _cards_from_products(results[:6])
        chips = plan.get("refinements") if isinstance(plan, dict) else None
        if not chips:
            chips = ["under $50", "breathable", "leather", "waterproof"]
        answer = _natural_reply_for_results(message, context, intent, cards, chips)  # type: ignore[arg-type]
        return AgentChatResponse(intent=intent, answer=answer, products=cards, refinements=chips)

    if intent == 'image_search':
        m = re.search(r"image:\s*([\w\-.]+)", message, flags=re.IGNORECASE)
        if not m:
            return AgentChatResponse(intent=intent, answer="Please provide your upload id as image:<upload_id>.", products=None, refinements=["upload first"])
        upload_id = m.group(1)
        try:
            # Reuse existing image search implementation
            from app.routers.tools import image_search as image_search_route

            items = image_search_route(ImageSearchRequest(upload_id=upload_id, k=12))
            products = items[:6]
            chips = plan.get("refinements") if isinstance(plan, dict) else None
            if not chips:
                chips = ["try another photo", "adjust budget"]
            answer = _natural_reply_for_results(message, context, intent, products, chips)  # type: ignore[arg-type]
            return AgentChatResponse(intent=intent, answer=answer, products=products, refinements=chips)
        except Exception as e:
            logger.warning(f"image search failed: {e}")
            return AgentChatResponse(intent=intent, answer="I couldn't run image search just now.", products=None, refinements=["try again"])

    if intent == 'catalog_qna':
        # Try UUID first
        m = re.search(r"([0-9a-fA-F-]{36})", message)
        prod: Optional[Product] = None
        if m:
            try:
                pid = uuid.UUID(m.group(1))
                with SessionLocal() as session:
                    prod = session.execute(sa.select(Product).where(Product.id == pid)).scalar_one_or_none()
            except Exception:
                prod = None

        # Fallback: extract likely title from the message and fuzzy match
        def _tokens(s: str) -> list[str]:
            t: list[str] = []
            buf: list[str] = []
            for ch in s.lower():
                if ch.isalnum() or ch in {"'", "-"}:
                    buf.append(ch)
                else:
                    if buf:
                        tok = "".join(buf)
                        if len(tok) > 2:
                            t.append(tok)
                        buf.clear()
            if buf:
                tok = "".join(buf)
                if len(tok) > 2:
                    t.append(tok)
            return t

        if not prod:
            # Pull quoted phrase if present, else part after common prompts (e.g., "tell me about")
            quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', message)
            candidate_text = None
            if quoted:
                # regex returns tuples from alternations; join non-empty
                for q in quoted[0]:
                    if q:
                        candidate_text = q
                        break
            if not candidate_text:
                m2 = re.search(r"(?i)(?:about|on|for)\s+(.+)$", message.strip())
                candidate_text = (m2.group(1) if m2 else message).strip()

            q_tokens = _tokens(candidate_text)
            if q_tokens:
                like_patterns = [f"%{tok}%" for tok in q_tokens[:6]]
                with SessionLocal() as session:
                    stmt = (
                        sa.select(Product)
                        .where(
                            sa.or_(
                                *[Product.title.ilike(p) for p in like_patterns],
                                *[Product.brand.ilike(p) for p in like_patterns],
                            )
                        )
                        .limit(25)
                    )
                    candidates = [row[0] for row in session.execute(stmt).all()]
                # Score candidates by token overlap with title+brand
                def score(p: Product) -> int:
                    hay = " ".join([p.title or "", p.brand or ""]).lower()
                    htoks = set(_tokens(hay))
                    return len(htoks.intersection(set(q_tokens)))

                if candidates:
                    candidates.sort(key=score, reverse=True)
                    if score(candidates[0]) > 0:
                        prod = candidates[0]

        if not prod:
            # Graceful fallback: treat as a browse request using extracted query tokens
            llm_query = (plan.get("query") if isinstance(plan, dict) else None) or message
            _fallback_query, fallback_filters = _parse_facets(llm_query)
            results = search_products(llm_query, fallback_filters, 12)
            cards = _cards_from_products(results[:6])
            chips = plan.get("refinements") if isinstance(plan, dict) else ["narrow by price", "filter by brand"]
            answer = _natural_reply_for_results(message, context, 'text_recommendation', cards, chips)  # type: ignore[arg-type]
            return AgentChatResponse(intent='text_recommendation', answer=answer, products=cards, refinements=chips)

        # Generate factual answer, then rewrite conversationally by LLM
        facts = answer_about_product(message, prod)
        answer = _rewrite_factual_answer(message, facts)
        card = ProductCard(
            id=str(prod.id), title=prod.title, brand=prod.brand, image_url=prod.image_url,
            price_cents=prod.price_cents, currency=prod.currency or "USD", in_stock=prod.in_stock, url=prod.url, badges=None
        )
        chips = plan.get("refinements") if isinstance(plan, dict) else None
        if not chips:
            chips = ["see similar items", "check sizes", "more like this"]
        return AgentChatResponse(intent=intent, answer=answer, products=[card], refinements=chips)

    # Default
    return AgentChatResponse(intent='chitchat', answer="Happy to help!", products=None, refinements=None)


