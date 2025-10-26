# test-case-generator Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-25

## Active Technologies
- Python 3.11+ + FastAPI (webhooks), LangGraph (AI workflow), Llama 3.2 (local server), PyGithub (GitHub operations) (001-ai-test-generation)
- Qdrant/ChromaDB (vector database for embeddings), Redis (1-hour idempotency cache) (001-ai-test-generation)

- Python 3.11+ + FastAPI (webhooks), LangGraph (AI workflow), OpenAI/Anthropic API, PyGithub (GitHub operations) (001-ai-test-generation)

## Project Structure

```text
backend/
  src/
    models/      # Pydantic data models
    services/    # Business logic
    api/         # FastAPI routes
    core/        # Config, logging, clients
  tests/         # Backend tests
  pyproject.toml # Python dependencies
frontend/
  src/
    components/  # React components
    pages/       # Route pages
    services/    # API client
  package.json   # Node dependencies
docker/          # Docker Compose and Dockerfiles
specs/           # Feature specifications
```

## Commands

cd backend; uv pip install -e ".[dev]"; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 001-ai-test-generation: Added Python 3.11+ + FastAPI (webhooks), LangGraph (AI workflow), Llama 3.2 (local server), PyGithub (GitHub operations)

- 001-ai-test-generation: Added Python 3.11+ + FastAPI (webhooks), LangGraph (AI workflow), OpenAI/Anthropic API, PyGithub (GitHub operations)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
