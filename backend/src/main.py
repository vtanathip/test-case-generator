"""FastAPI application factory."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from src.core.config import settings
from src.core.logging import setup_logging, bind_correlation_id, unbind_correlation_id
from src.core.exceptions import TestCaseGeneratorException
from src.api import health

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    # Setup logging
    setup_logging(
        log_level=settings.backend_log_level,
        json_logs=not settings.debug
    )
    
    # Create app
    app = FastAPI(
        title="AI Test Case Generator",
        description="Automated test case generation from GitHub issues",
        version="0.1.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    @app.exception_handler(TestCaseGeneratorException)
    async def app_exception_handler(
        request: Request, 
        exc: TestCaseGeneratorException
    ) -> JSONResponse:
        """Handle application exceptions."""
        logger.error(
            "application_error",
            error_code=exc.error_code,
            message=str(exc),
            details=exc.details
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": exc.error_code,
                "message": str(exc),
                "details": exc.details
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, 
        exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception("unexpected_error", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "E500",
                "message": "Internal server error",
            }
        )
    
    # Request middleware for correlation ID
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Add correlation ID to all requests."""
        import uuid
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        bind_correlation_id(correlation_id)
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        unbind_correlation_id()
        return response
    
    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        logger.info("application_starting", version="0.1.0")
        # TODO: Initialize Redis, ChromaDB, Ollama clients
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("application_shutting_down")
        # TODO: Close Redis, ChromaDB, Ollama connections
    
    return app


app = create_app()
