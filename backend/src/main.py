"""FastAPI application entrypoint.

AI Code Generation and Analysis Platform
- POST /api/v1/generate  — Code generation with LLM routing
- POST /api/v1/analyze   — Concurrent static + LLM analysis
- GET  /api/v1/history   — Paginated request history
- GET  /health           — Health check endpoint
"""

import logging
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.database import init_db
from src.routes import generate_router, analyze_router, history_router

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle manager."""
    logger.info("Starting AI Code Platform API...")
    await init_db()
    logger.info("Database tables initialized.")
    yield
    logger.info("Shutting down AI Code Platform API.")


# ─── App Instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Code Generation & Analysis Platform",
    description=(
        "A full-stack platform featuring Monaco Editor integration with intelligent "
        "LLM routing. Routes simple generation tasks to fast Groq/Llama3 models and "
        "complex analysis tasks to reasoning frontier models (GPT-4o/Gemini). "
        "Combines static analysis (Pylint/ESLint) with AI code review."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global Exception Handlers ────────────────────────────────────────────────
@app.exception_handler(httpx.TimeoutException)
async def timeout_exception_handler(request: Request, exc: httpx.TimeoutException):
    """Return 504 for unhandled LLM timeout exceptions."""
    logger.error("Unhandled timeout: %s", exc)
    return JSONResponse(
        status_code=504,
        content={
            "error": "Gateway Timeout",
            "detail": "An upstream service timed out. Please try again.",
            "code": "TIMEOUT",
        },
    )


@app.exception_handler(httpx.HTTPStatusError)
async def http_status_error_handler(request: Request, exc: httpx.HTTPStatusError):
    """Return 502 for unhandled upstream HTTP errors."""
    logger.error("Unhandled upstream HTTP error: %s", exc)
    return JSONResponse(
        status_code=502,
        content={
            "error": "Bad Gateway",
            "detail": f"An upstream service returned an error: {exc.response.status_code}",
            "code": "BAD_GATEWAY",
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected server errors."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again.",
            "code": "INTERNAL_ERROR",
        },
    )


# ─── Routes ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(generate_router, prefix=API_PREFIX, tags=["Generation"])
app.include_router(analyze_router, prefix=API_PREFIX, tags=["Analysis"])
app.include_router(history_router, prefix=API_PREFIX, tags=["History"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/", tags=["Root"])
async def root():
    """API root with links to documentation."""
    return {
        "name": "AI Code Generation & Analysis Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
