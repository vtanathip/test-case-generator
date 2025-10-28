"""FastAPI application factory."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import health, jobs, webhooks
from src.core.config import settings
from src.core.exceptions import TestCaseGeneratorException
from src.core.logging import bind_correlation_id, setup_logging, unbind_correlation_id

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)."""
    # Startup
    logger.info("application_starting", version="0.1.0")

    # Initialize in-memory job storage (will be replaced with Redis)
    app.state.jobs = {}

    try:
        # Initialize real clients
        from src.core.cache import RedisClient
        from src.core.embeddings import EmbeddingService
        from src.core.github_client import GitHubClient
        from src.core.llm_client import LLMClient
        from src.core.vector_db import VectorDBClient

        logger.info("initializing_clients")

        # Initialize Redis cache
        app.state.redis_client = RedisClient(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
        await app.state.redis_client.connect()
        logger.info("redis_client_ready")

        # Initialize Vector DB
        app.state.vector_db = VectorDBClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
            collection_name=settings.chromadb_collection
        )
        await app.state.vector_db.connect()
        logger.info("vector_db_client_ready")

        # Initialize LLM client
        app.state.llm_client = LLMClient(
            host=settings.ollama_host,
            model=settings.llama_model,
            timeout=settings.ollama_timeout
        )
        await app.state.llm_client.connect()
        logger.info("llm_client_ready", model=settings.llama_model,
                    host=settings.ollama_host)

        # Initialize GitHub client
        app.state.github_client = GitHubClient(
            token=settings.github_token,
            timeout=settings.github_api_timeout
        )
        logger.info("github_client_ready")

        # Initialize Embedding service
        app.state.embedding_service = EmbeddingService(
            model_name=settings.chromadb_embedding_model
        )
        app.state.embedding_service.load_model()
        logger.info("embedding_service_ready")

    except Exception as e:
        logger.error("client_initialization_failed",
                     error=str(e), error_type=type(e).__name__)
        raise

    # Initialize services
    from src.services.ai_service import AIService
    from src.services.github_service import GitHubService
    from src.services.webhook_service import WebhookService

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
    await app.state.redis_client.disconnect()
    await app.state.vector_db.disconnect()
    await app.state.llm_client.disconnect()


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
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid.uuid4()))
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
