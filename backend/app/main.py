from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from .core.logging import configure_logging
from .core.settings import get_settings
from .routers.tools import router as tools_router
from .routers.products import router as products_router
from .routers.agent import router as agent_router


configure_logging()
settings = get_settings()

app = FastAPI()
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

# CORS configuration based on settings.ALLOW_ORIGINS (with sensible defaults for Next.js)
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_allow_origins = settings.allow_origins or _default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory ready at: {upload_path.resolve()}")

    # Routers
    app.include_router(tools_router)
    app.include_router(products_router)
    app.include_router(agent_router)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail or "Request error"})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "Invalid request", "details": exc.errors()})


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


