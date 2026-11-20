import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.ai.rag.qdrant_manager import qdrant_manager
from app.core.config import settings
from app.core.database import Base, sync_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("querymind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database tables, vector indices and resources on startup."""
    logger.info("Initializing QueryMind AI Backend services...")
    # 1. Verify/create relational database tables
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("PostgreSQL application tables ready.")
    except Exception as e:
        logger.error(f"Error initializing PostgreSQL tables: {e}")

    # 2. Ensure Qdrant collection
    try:
        qdrant_manager.ensure_collection()
        logger.info("Qdrant vector collection ready.")
    except Exception as e:
        logger.warning(f"Error checking Qdrant on startup: {e}")

    yield

    logger.info("Shutting down QueryMind AI Backend.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Your Data. Your Questions. Intelligent Answers. Enterprise AI Database & SQL Copilot.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root_endpoint():
    """Root info endpoint."""
    return {
        "app": settings.APP_NAME,
        "tagline": "Your Data. Your Questions. Intelligent Answers.",
        "version": "1.0.0",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "primary_llm_provider": settings.LLM_PROVIDER,
        "primary_model": settings.GEMINI_MODEL,
        "status": "online",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global safe exception handler that avoids leaking internal stack traces."""
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again or check system logs."},
    )

