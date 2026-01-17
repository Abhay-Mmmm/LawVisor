"""
LawVisor - Multi-Modal Legal AI Assistant
==========================================
Main FastAPI application entry point.

This application provides:
- PDF document upload and processing
- OCR and text extraction
- Legal clause extraction and classification
- RAG-based compliance analysis against GDPR/SEC
- Explainable risk scoring

Author: LawVisor Team
Version: 1.0.0
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import analyze_router, risk_router, upload_router
from core.config import get_settings
from core.regulations import get_regulations_fetcher
from schemas import ErrorResponse, HealthCheckResponse

# === Configuration ===
settings = get_settings()


# === Logging Setup ===
def setup_logging():
    """Configure structured logging."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure root logger
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


setup_logging()
logger = structlog.get_logger(__name__)


# === Lifespan Management ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.
    
    Startup:
    - Validate configuration
    - Initialize services
    - Create upload directory
    
    Shutdown:
    - Close connections
    - Cleanup resources
    """
    logger.info("Starting LawVisor API", version="1.0.0")
    
    # Validate configuration
    try:
        settings.validate_llm_config()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error("Configuration error", error=str(e))
        # Continue startup but log warning
    
    # Ensure upload directory exists
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready", path=str(settings.upload_dir))
    
    # Ensure cache directory exists
    cache_dir = Path("./cache/regulations")
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Cache directory ready", path=str(cache_dir))
    
    yield
    
    # Cleanup
    logger.info("Shutting down LawVisor API")
    
    # Close regulations fetcher
    fetcher = get_regulations_fetcher()
    await fetcher.close()


# === Application Setup ===
app = FastAPI(
    title="LawVisor API",
    description="""
    ## Multi-Modal Legal AI Assistant
    
    LawVisor is an enterprise-grade legal document analysis platform that:
    
    - **Accepts** PDF legal contracts (scanned or native)
    - **Extracts** structured clauses using OCR + Vision-Language Models
    - **Identifies** legal risks at the clause level
    - **Cross-verifies** clauses against live regulatory sources (GDPR, SEC)
    - **Produces** explainable Risk Scores with citations
    
    ### Key Features
    
    - 🔍 **Smart OCR**: Handles both scanned and native PDFs
    - 📋 **Clause Classification**: 18+ legal clause types
    - ⚖️ **Compliance Analysis**: GDPR and SEC regulations
    - 📊 **Risk Scoring**: 0-100 scale with full explainability
    - 📚 **Citations**: Every decision is backed by regulatory sources
    
    ### API Flow
    
    1. `POST /upload` - Upload a PDF document
    2. `POST /analyze/{document_id}` - Analyze the document
    3. `GET /risk/{document_id}` - Retrieve the full risk report
    
    ### Rate Limits
    
    - 100 requests per minute per IP
    - Max file size: 50MB
    """,
    version="1.0.0",
    contact={
        "name": "LawVisor Support",
        "email": "support@lawvisor.ai"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# === CORS Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "https://*.vercel.app",   # Vercel deployments
        "https://*.netlify.app",  # Netlify deployments
        "*",                      # Allow all for development/testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Exception Handlers ===
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.exception("Unhandled exception", path=request.url.path, error=str(exc))
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please try again.",
            "details": {"path": request.url.path} if settings.debug else None
        }
    )


# === Health Check ===
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health check",
    description="Check if the API is running and all services are available."
)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.
    
    Returns the status of the API and dependent services.
    """
    services = {
        "api": "healthy",
        "ocr": "healthy",
        "llm": "unknown"  # Would check API connectivity in production
    }
    
    # Check if LLM is configured (OpenAI)
    if settings.openai_api_key:
        services["llm"] = "configured"
    else:
        services["llm"] = "not_configured"
    
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        services=services
    )


@app.get(
    "/",
    tags=["Health"],
    summary="Root endpoint",
    description="Welcome message and API information."
)
async def root():
    """Root endpoint with welcome message."""
    return {
        "name": "LawVisor API",
        "version": "1.0.0",
        "description": "Multi-Modal Legal AI Assistant",
        "docs": "/docs",
        "health": "/health"
    }


# === Register Routers ===
app.include_router(upload_router)
app.include_router(analyze_router)
app.include_router(risk_router)


# === Main Entry Point ===
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
