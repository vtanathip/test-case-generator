"""FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from src.core.config import settings
from src.core.logging import setup_logging, bind_correlation_id, unbind_correlation_id
from src.core.exceptions import TestCaseGeneratorException
from src.api import health, webhooks, jobs

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)."""
    # Startup
    logger.info("application_starting", version="0.1.0")
    
    # Initialize in-memory job storage (will be replaced with Redis)
    app.state.jobs = {}
    
    # TODO: Initialize actual clients (Redis, ChromaDB, Ollama, GitHub)
    # For now, use mocks/stubs for testing
    from unittest.mock import AsyncMock, Mock
    
    # Create mock clients (will be replaced with real implementations)
    app.state.redis_client = Mock()
    app.state.redis_client.exists = AsyncMock(return_value=False)
    app.state.redis_client.set_with_ttl = AsyncMock()
    
    app.state.vector_db = Mock()
    app.state.vector_db.query_similar = AsyncMock(return_value=[])
    
    app.state.llm_client = Mock()
    app.state.llm_client.generate = AsyncMock(return_value="# Test Cases\\n\\nGenerated test cases...")
    
    app.state.github_client = Mock()
    app.state.github_client.create_branch = AsyncMock()
    app.state.github_client.create_or_update_file = AsyncMock()
    app.state.github_client.create_pull_request = AsyncMock(return_value={"number": 1, "html_url": "https://github.com/owner/repo/pull/1"})
    app.state.github_client.add_issue_comment = AsyncMock()
    
    app.state.embedding_service = Mock()
    
    # Initialize services
    from src.services.webhook_service import WebhookService
    from src.services.ai_service import AIService
    from src.services.github_service import GitHubService
    
    app.state.webhook_service = WebhookService(
        redis_client=app.state.redis_client,
        config=settings
    )
    
    app.state.ai_service = AIService(
        llm_client=app.state.llm_client,
        vector_db=app.state.vector_db,
        embedding_service=app.state.embedding_service,
        github_client=app.state.github_client,
        redis_client=app.state.redis_client,
        config=settings
    )
    
    app.state.github_service = GitHubService(
        github_client=app.state.github_client,
        config=settings
    )
    
    logger.info("services_initialized")
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    # TODO: Close Redis, ChromaDB, Ollama connections


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
    
    # Create app with lifespan
    app = FastAPI(
        title="AI Test Case Generator",
        description="Automated test case generation from GitHub issues",
        version="0.1.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan
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
    app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    
    return app


app = create_app()
