Hey Kelvin! Hope you are having a great day today. It's Ralfi and this is my minimal implementation for the Rufus-like chatbot. I believe there is much further work that could be done. Please let me know with any more features/reqs that you wish me to update this repo with. Hope to get in contact soon and your feedback. Have a good one.

Palona Monorepo: A single‑agent commerce assistant that unifies conversational shopping via chat, text search, and image‑based search. The assistant integrates product discovery, visual lookup, and product Q&A into one experience across backend, frontend, scripts, and data layers.

## Overview

Palona is a full‑stack demo that showcases:

- Conversational agent that routes between intents: chitchat, text recommendations, image search, and catalog Q&A
- Vector search over a product catalog using `pgvector`
- Image similarity search using CLIP embeddings
- Next.js frontend with simple chat UI, product grid, and product detail

### Architecture

```
+-----------------------+          +---------------------------+
|     Next.js (15)      |  /api →  | FastAPI (backend)        |
| - Chat UI             |────────▶ | - /agent/chat             |
| - Product detail page |          | - /tools/*                |
| - Image upload        | ◀────────| - /products/*             |
+-----------------------+  images  +-------------┬-------------+
            │                         SQLAlchemy  │  Embeddings
            │ rewrites                           │
            ▼                                     ▼
       http://localhost:8000              +--------------------+
                                           | PostgreSQL +      |
                                           | pgvector          |
                                           | (product, event)  |
                                           +--------------------+
```

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ with the `pgvector` extension

### Backend

1. Create a Postgres database and enable extensions:
   - Install extension once: `CREATE EXTENSION IF NOT EXISTS vector;`
   - Optional (text ops): `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
2. Create `backend/.env` and update values:
   - `DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/palona`
   - Optional: `OPENAI_API_KEY=...`
   - Optional: `EMBEDDING_MODEL=text-embedding-3-small`
   - Optional: `CHAT_MODEL=gpt-4o-mini`
   - Optional: `ALLOW_ORIGINS=http://localhost:3000`
   - Optional: `UPLOAD_DIR=uploads`
3. Install, migrate, ingest, run:
   - `cd backend`
   - `pip install -e .`
   - `alembic upgrade head`
   - Ingest sample catalog: `make ingest` (uses `data/catalog.sample.json`)
   - Start API: `make run` (Uvicorn on port 8000)

### Frontend

1. Create `frontend/.env.local` (optional when server URL differs):
   - `API_BASE_URL=http://localhost:8000`
2. Install and run:
   - `cd frontend`
   - `npm install`
   - `npm run dev` (Next.js on http://localhost:3000)

The frontend uses Next.js rewrites to proxy `/api/*` to `http://localhost:8000/*` and `/api/uploads` to `/tools/uploads` on the backend. Uploaded images are served from `/uploads/*`.

## Environment Variables

### Backend (`backend/.env`)

- `DATABASE_URL` (required): SQLAlchemy URL (e.g., `postgresql+psycopg2://user:pass@localhost:5432/palona`)
- `OPENAI_API_KEY` (optional): enables LLM‑powered intent routing and answers
- `EMBEDDING_MODEL` (default: `text-embedding-3-small`)
- `CHAT_MODEL` (default: `gpt-4o-mini` or `gpt-5-mini-2025-08-07`)
- `ALLOW_ORIGINS` (optional): CSV or JSON list for CORS
- `UPLOAD_DIR` (default: `uploads`)

Sample backend `.env`:

```bash
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/palona
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o-mini
ALLOW_ORIGINS=http://localhost:3000
UPLOAD_DIR=uploads
```

### Frontend (`frontend/.env.local`)

- `API_BASE_URL` (optional for SSR product pages; default `http://localhost:8000`)

Sample frontend `.env.local`:

```bash
API_BASE_URL=http://localhost:8000
```

## API Reference

Base URL: `http://localhost:8000`

### POST /agent/chat

Request

```
{
  "message": "running shoes under $100",
  "context": [{"role":"user","content":"..."}]
}
```

Response

```
{
  "intent": "text_recommendation",
  "answer": "Here are some picks...",
  "products": [
    {"id":"...","title":"...","brand":"...","image_url":"...","price_cents":9999,"currency":"USD","in_stock":true,"url":"...","badges":["in_stock"]}
  ],
  "refinements": ["under $50","breathable"]
}
```

### POST /tools/product.search

Request

```
{
  "query": "leather boots",
  "filters": {
    "price_min_cents": 5000,
    "price_max_cents": 20000,
    "brand": ["Acme"]
  },
  "k": 12
}
```

Response (200)

```
[
  {"id":"...","title":"...","brand":"...","image_url":"...","price_cents":14999,"currency":"USD","in_stock":true,"url":"...","badges":["top_rated"]}
]
```

### POST /tools/product.recommend

Request

```
{
  "use_case": "hiking in winter",
  "constraints": {"category":["Jackets"], "price_max_cents": 20000},
  "k": 12
}
```

Response (200)

```
[
  {
    "product": {"id":"...","title":"...","brand":"...","image_url":"...","price_cents":19999,"currency":"USD","in_stock":true,"url":"...","badges":["in_stock"]},
    "reason": "within budget; category match"
  }
]
```

### POST /tools/image.search

Request

```
{
  "upload_id": "<returned from /tools/uploads>",
  "k": 12
}
```

Response (200)

```
[
  {"id":"...","title":"...","brand":"...","image_url":"...","price_cents":12999,"currency":"USD","in_stock":true,"url":"...","badges":["budget"]}
]
```

### POST /tools/uploads

Multipart form‑data

```
file: <image/*>
```

Response (200)

```
{ "upload_id": "<id>.jpg", "url": "/uploads/<id>.jpg" }
```

### GET /products/{id}

Response (200)

```
{
  "id": "...",
  "title": "...",
  "brand": "...",
  "image_url": "...",
  "price_cents": 14999,
  "currency": "USD",
  "in_stock": true,
  "url": "...",
  "badges": null,
  "category": ["Jackets"],
  "description": "...",
  "color": ["Black"],
  "material": ["Polyester"],
  "size": ["S","M","L"],
  "gender": "men",
  "attributes": {"waterproof": true},
  "rating": 4.5,
  "keywords": ["hiking","waterproof"]
}
```

## Latency, Cost, Limitations, and Future Work

- Latency:
  - Text search uses OpenAI embeddings on first‑seen queries; results are cached per normalized text. Subsequent searches are fast (single SQL round‑trip).
  - Image search runs CLIP locally (SentenceTransformers) which can be CPU‑bound; vector KNN over `pgvector` is sub‑100ms for small catalogs.
- Cost:
  - LLM features (intent routing, natural replies) call OpenAI when `OPENAI_API_KEY` is set. Embeddings also incur cost for new queries.
  - Running without an API key falls back to heuristic routing and canned responses.
- Limitations:
  - No authentication or per‑user sessions in storage; rate limiting is in‑memory.
  - Catalog is a sample; ingestion assumes a normalized schema and may skip malformed items.
  - Image search uses a single CLIP model and naive color fallback when embeddings or vectors are unavailable.
- Future Work:
  - Streaming responses and tool‑calling plans for richer agent UX.
  - Reranking with cross‑encoders; more robust facet extraction; telemetry and tracing.
  - Persistent sessions, shortlist/favorites, and checkout handoff.
  - Batch embedding pipeline and background workers for ingestion at scale.
