# Developer Guide: AI Test Case Generation System

**Last Updated**: 2025-01-20  
**Branch**: `001-ai-test-generation`  
**Status**: Phase 3 Complete (100%)

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Running the Application](#running-the-application)
4. [Running Tests](#running-tests)
5. [Development Workflow](#development-workflow)
6. [Architecture Overview](#architecture-overview)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **Python** | 3.11+ | Backend runtime | [python.org](https://www.python.org/downloads/) |
| **Docker Desktop** | 24.0+ | Container orchestration | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Docker Compose** | 2.20+ | Multi-container management | Included with Docker Desktop |
| **uv** | Latest | Fast Python package installer | `pip install uv` |
| **Git** | 2.30+ | Version control | [git-scm.com](https://git-scm.com/) |
| **Node.js** | 18+ | Frontend tooling | [nodejs.org](https://nodejs.org/) (for dashboard) |

### Optional Tools

- **GPU**: NVIDIA GPU with 8GB+ VRAM (for Llama 3.2 11B model)
  - *CPU-only*: Use `llama3.2:3b` model (slower but functional)
- **VS Code**: Recommended IDE with Python extension
- **GitHub CLI**: For quick PR/issue management (`gh`)

### System Requirements

- **OS**: Linux, macOS, or Windows with WSL2
- **RAM**: 8GB minimum (16GB recommended for GPU models)
- **Disk**: 20GB free space (for Docker images and models)
- **Network**: Stable internet for Docker image pulls and GitHub API

---

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/owner/test-case-generator.git
cd test-case-generator
```

### 2. Install uv Package Manager

**Why uv?** Fast Python package installer (10-100x faster than pip). See [docs/uv-setup.md](./uv-setup.md) for details.

```bash
# Install uv
pip install uv

# Verify installation
uv --version
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment with uv
uv venv

# Activate virtual environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies (includes dev tools)
uv pip install -e ".[dev]"

# Verify installation
python -c "import fastapi, langgraph; print('✓ Backend dependencies installed')"
```

**Dependencies Installed**:
- **Core**: FastAPI, LangGraph, Pydantic, PyGithub
- **Storage**: ChromaDB, Redis
- **Testing**: pytest, pytest-asyncio, httpx
- **Quality**: ruff (linter), black (formatter), mypy (type checker)

### 4. Frontend Setup (Dashboard)

```bash
cd frontend

# Install Node dependencies
npm install

# Verify installation
npm run build -- --help
```

### 5. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required variables:
```

**Required Environment Variables**:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx          # Personal access token (repo scope)
GITHUB_WEBHOOK_SECRET=your_secret_here  # Random 32-char string
GITHUB_REPO=owner/repo                  # Repository full name

# Llama 3.2 Configuration
LLAMA_MODEL=llama3.2:11b                # Model variant (3b, 11b, or 90b)
OLLAMA_HOST=ollama                      # Ollama hostname (docker service)

# Vector Database (ChromaDB)
CHROMADB_HOST=chromadb                  # ChromaDB hostname
CHROMADB_PORT=8000                      # ChromaDB port

# Cache (Redis)
REDIS_HOST=redis                        # Redis hostname
REDIS_PORT=6379                         # Redis port
REDIS_TTL=3600                          # Idempotency cache TTL (1 hour)

# Cloudflare Tunnel (for webhook endpoint)
CLOUDFLARE_TUNNEL_TOKEN=xxx             # Named Tunnel: Get from dashboard
                                        # Quick Tunnel: Not needed (for dev/test)

# Logging
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
STRUCTURED_LOGGING=true                 # Enable JSON logging
```

**Getting GitHub Token**:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with scopes: `repo`, `admin:repo_hook`
3. Copy token to `GITHUB_TOKEN` in `.env`

**Cloudflare Tunnel Options**:

- **Quick Tunnel** (Experimental/Dev - Recommended for testing):
  - No configuration needed in `.env`
  - Run: `cloudflared tunnel --url http://localhost:8000`
  - URL changes on restart (manual webhook update required)
  - Download: <https://github.com/cloudflare/cloudflared/releases/latest>

- **Named Tunnel** (Production):
  - Persistent URL, requires Cloudflare account
  - Set `CLOUDFLARE_TUNNEL_TOKEN` in `.env`
  - See: <https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/>


---

## Running the Application

### Option 1: Docker Compose (Recommended)

**Start all services** (backend, frontend, ChromaDB, Redis, Ollama):

```bash
# Start services in background
docker-compose up -d

# Pull Llama 3.2 model (first time only, ~5-10 minutes)
docker-compose exec ollama ollama pull llama3.2:latest

# Check service status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f backend
```

**Stop services**:

```bash
docker-compose down                # Stop and remove containers
docker-compose down -v             # Also remove volumes (data loss!)
```

### Option 2: Local Development (Backend Only)

**Terminal 1 - Start dependencies**:

```bash
# Start ChromaDB, Redis, Ollama via Docker
docker-compose up -d chromadb redis ollama

# Pull Llama model
docker-compose exec ollama ollama pull llama3.2:11b
```

**Terminal 2 - Run backend**:

```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

# Start FastAPI backend (auto-reload enabled)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 - Run frontend** (optional):

```bash
cd frontend

# Start development server
npm run dev

# Access dashboard at http://localhost:3000
```

### Option 3: Full Local Development

**Without Docker** (requires manual setup of ChromaDB, Redis, Ollama):

```bash
# Not recommended for beginners
# See docs/local-setup-without-docker.md (if exists)
```

---

## Running Tests

### Quick Test Commands

```bash
cd backend
source .venv/bin/activate  # Activate virtual environment

# Run all tests (90 tests, ~3 minutes)
pytest

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test types
pytest tests/unit/                  # Unit tests only (69 tests, fast)
pytest tests/integration/           # Integration tests (6 tests, slower)
pytest tests/contract/              # Contract tests (15 tests, GitHub API schemas)

# Run specific test file
pytest tests/unit/services/test_webhook_service.py -v

# Run specific test function
pytest tests/unit/models/test_webhook_event.py::test_webhook_event_creation -v

# Run tests matching pattern
pytest -k "webhook" -v              # All tests with "webhook" in name

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Verbose output
pytest -v

# Quiet mode (show only summary)
pytest -q

# Run failed tests from last run
pytest --lf
```

### Test Coverage

**Current Coverage**: 68% (target: 80%)

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open report in browser
# Windows:
start htmlcov/index.html
# macOS:
open htmlcov/index.html
# Linux:
xdg-open htmlcov/index.html
```

**Coverage by Module**:
- `src/models/`: 95%+ (high coverage, simple validation)
- `src/services/`: 70-85% (good coverage, complex logic)
- `src/api/`: 60-75% (moderate coverage, needs more integration tests)
- `src/core/`: 50-70% (lower coverage, infrastructure code)

**Improving Coverage**:
- Add unit tests for uncovered branches
- Add integration tests for API endpoints
- Add contract tests for external API calls

### Test Types

#### 1. Unit Tests (69 tests)

**Purpose**: Test individual functions/classes in isolation

**Location**: `tests/unit/`

**Examples**:
```bash
# Test data models
pytest tests/unit/models/ -v

# Test services
pytest tests/unit/services/ -v

# Test core utilities
pytest tests/unit/core/ -v
```

**Characteristics**:
- Fast execution (<1 second per test)
- No external dependencies (mocked)
- High coverage (95%+ target)

#### 2. Integration Tests (6 tests)

**Purpose**: Test end-to-end workflows with real components

**Location**: `tests/integration/`

**Examples**:
```bash
# Test full webhook → AI → PR workflow
pytest tests/integration/test_e2e_workflow.py -v

# Test GitHub API integration
pytest tests/integration/test_github_integration.py -v
```

**Characteristics**:
- Slower execution (5-30 seconds per test)
- Uses real ChromaDB, Redis (Docker containers)
- Tests realistic scenarios

#### 3. Contract Tests (15 tests)

**Purpose**: Validate GitHub API response schemas

**Location**: `tests/contract/`

**Examples**:
```bash
# Test GitHub API contracts
pytest tests/contract/ -v
```

**Characteristics**:
- Medium execution speed (1-5 seconds per test)
- Uses real GitHub API (requires token)
- Ensures API compatibility

### Linting and Code Quality

```bash
# Run ruff linter (check code style)
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Check types with mypy
mypy src/

# Format code with black (if configured)
black src/ tests/
```

**Quality Targets**:
- Zero ruff errors (enforced in CI)
- Zero mypy errors for strict-typed modules
- 100% passing tests before PR merge

---

## Development Workflow

### 1. Test-Driven Development (TDD)

**Recommended workflow** for new features:

```bash
# 1. Write failing test
vim tests/unit/services/test_new_feature.py

# 2. Run test (should fail)
pytest tests/unit/services/test_new_feature.py -v

# 3. Write minimal code to pass test
vim src/services/new_feature.py

# 4. Run test (should pass)
pytest tests/unit/services/test_new_feature.py -v

# 5. Refactor and repeat
```

### 2. Git Workflow

**Branch naming**:
```bash
# Feature branches
git checkout -b feature/add-retry-logic

# Bug fixes
git checkout -b fix/webhook-signature-validation

# Documentation
git checkout -b docs/update-developer-guide
```

**Commit messages**:
```bash
# Good commit messages (conventional commits)
git commit -m "feat: add exponential backoff retry logic"
git commit -m "fix: correct webhook signature validation"
git commit -m "docs: update developer guide with test commands"
git commit -m "test: add integration test for PR creation"

# Commit types: feat, fix, docs, test, refactor, chore
```

**Pull request checklist**:
- [ ] All tests pass (`pytest`)
- [ ] No linting errors (`ruff check .`)
- [ ] Coverage maintained or improved
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated (if user-facing change)

### 3. Code Style

**Python conventions** (enforced by ruff):
- PEP 8 compliant
- Max line length: 100 characters
- Type hints required for public APIs
- Docstrings required for modules, classes, public functions

**Example**:
```python
from typing import Optional

def process_webhook(
    payload: bytes,
    signature: str,
    event_type: str
) -> WebhookEvent:
    """
    Process incoming GitHub webhook event.
    
    Args:
        payload: Raw webhook payload bytes
        signature: HMAC-SHA256 signature from GitHub
        event_type: GitHub event type (e.g., "issues.opened")
    
    Returns:
        Validated WebhookEvent model
    
    Raises:
        InvalidWebhookSignatureError: If signature verification fails
        InvalidWebhookPayloadError: If payload structure is invalid
    """
    # Implementation...
```

### 4. Debugging

**Print debugging** (structured logs):
```python
import structlog

log = structlog.get_logger(__name__)

# Use structured logging (NOT print statements)
log.info("processing_webhook", issue_number=123, labels=["generate-tests"])
log.error("failed_to_create_pr", error=str(e), correlation_id=correlation_id)
```

**Interactive debugging** (pdb):
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

**VS Code debugging**:
1. Set breakpoint in code (click left margin)
2. Press F5 or Run → Start Debugging
3. Select "Python: FastAPI" configuration

---

## Architecture Overview

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI (Python 3.11+) | REST API, webhook handling |
| **AI Workflow** | LangGraph | State machine for 6-stage workflow |
| **AI Model** | Llama 3.2 (via Ollama) | Local LLM for test case generation |
| **Vector DB** | ChromaDB | Embedding storage and similarity search |
| **Cache** | Redis | Idempotency tracking (1-hour TTL) |
| **GitHub API** | PyGithub | Branch, commit, PR operations |
| **Frontend** | React 18 + TypeScript | Dashboard UI (optional) |
| **Testing** | pytest + httpx | Unit, integration, contract tests |

### Project Structure

```text
test-case-generator/
├── backend/                    # Python backend
│   ├── src/
│   │   ├── models/             # Pydantic data models
│   │   │   ├── webhook_event.py
│   │   │   ├── processing_job.py
│   │   │   └── test_case_document.py
│   │   ├── services/           # Business logic
│   │   │   ├── webhook_service.py   # Webhook validation
│   │   │   ├── ai_service.py        # LangGraph workflow
│   │   │   └── github_service.py    # GitHub API client
│   │   ├── api/                # FastAPI routes
│   │   │   ├── webhooks.py     # POST /webhooks/github
│   │   │   ├── health.py       # GET /health
│   │   │   └── jobs.py         # GET /api/jobs (dashboard)
│   │   └── core/               # Infrastructure
│   │       ├── config.py       # Environment variables
│   │       ├── logging.py      # Structured logging setup
│   │       ├── cache.py        # Redis client
│   │       ├── vector_db.py    # ChromaDB client
│   │       └── llm_client.py   # Ollama client
│   ├── tests/                  # All tests
│   │   ├── unit/               # Unit tests (69 tests)
│   │   ├── integration/        # Integration tests (6 tests)
│   │   └── contract/           # Contract tests (15 tests)
│   └── pyproject.toml          # Python dependencies (uv)
├── frontend/                   # React dashboard (optional)
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Route pages
│   │   └── services/           # API client
│   └── package.json            # Node dependencies
├── docs/                       # Documentation
│   ├── DEVELOPER_GUIDE.md      # This file
│   ├── langgraph-implementation.md  # LangGraph details
│   └── uv-setup.md             # uv package manager guide
├── specs/                      # Feature specifications
│   └── 001-ai-test-generation/
│       ├── spec.md             # Main specification
│       ├── plan.md             # Implementation plan
│       ├── tasks.md            # Task breakdown
│       ├── data-model.md       # Data models
│       ├── error-catalog.md    # Error codes
│       └── ...                 # (26 spec files)
├── docker/                     # Docker configurations
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml          # Multi-container setup
├── .env.example                # Environment template
└── README.md                   # Project overview
```

### Data Flow

```text
1. GitHub Issue Created (with "generate-tests" label)
        ↓
2. GitHub sends webhook → Cloudflare Tunnel → FastAPI Backend
        ↓
3. WebhookService validates signature, checks idempotency
        ↓
4. Create ProcessingJob (status: PENDING → PROCESSING)
        ↓
5. AIService (LangGraph 6-stage workflow):
   ┌─────────────────────────────────────────────────┐
   │ RECEIVE:    Validate webhook, parse issue       │
   │ RETRIEVE:   Query ChromaDB for similar tests    │
   │ GENERATE:   Llama 3.2 generates test cases      │
   │ COMMIT:     Create branch, commit Markdown file │
   │ CREATE_PR:  Open pull request                   │
   │ FINALIZE:   Add comment, update job status      │
   └─────────────────────────────────────────────────┘
        ↓
6. GitHubService creates PR with test cases
        ↓
7. ProcessingJob status: COMPLETED
        ↓
8. Dashboard UI displays results (optional)
```

### Workflow Stages (LangGraph)

See [docs/langgraph-implementation.md](./langgraph-implementation.md) for detailed state machine.

**6 Stages**:
1. **RECEIVE**: Webhook validation, event parsing
2. **RETRIEVE**: Vector DB similarity search (top 5 results)
3. **GENERATE**: AI test case generation (Llama 3.2)
4. **COMMIT**: Git operations (branch, commit)
5. **CREATE_PR**: Pull request creation
6. **FINALIZE**: Issue comment, cleanup

**Error Handling**:
- **Retry Logic**: Exponential backoff (5s, 15s, 45s) for transient errors (E3xx, E4xx)
- **Idempotency**: 1-hour cache prevents duplicate processing
- **Correlation IDs**: Track requests across all stages
- **Structured Logging**: JSON logs with correlation_id, stage, error_code

---

## Troubleshooting

### Common Issues

#### 1. Tests Failing: "structlog" error

**Error**:
```
TypeError: got multiple values for argument 'event'
```

**Cause**: Incorrect structlog logging call (passing `event` twice)

**Fix**:
```python
# ❌ Wrong (event passed twice: positional + keyword)
log.info("webhook_received", event="webhook_data", issue_number=123)

# ✅ Correct (first positional argument IS the event)
log.info("webhook_received", issue_number=123, labels=["generate-tests"])
```

#### 2. Docker Compose: "Cannot connect to Docker daemon"

**Error**:
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Cause**: Docker Desktop not running

**Fix**:
```bash
# Start Docker Desktop
# Windows: Open Docker Desktop from Start Menu
# macOS: Open Docker Desktop from Applications
# Linux: sudo systemctl start docker

# Verify Docker is running
docker ps
```

#### 3. Backend: "Module not found" error

**Error**:
```
ModuleNotFoundError: No module named 'fastapi'
```

**Cause**: Virtual environment not activated or dependencies not installed

**Fix**:
```bash
cd backend

# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

# Reinstall dependencies
uv pip install -e ".[dev]"

# Verify installation
python -c "import fastapi; print(fastapi.__version__)"
```

#### 4. Tests: "No module named 'pytest'"

**Cause**: Dev dependencies not installed

**Fix**:
```bash
cd backend
source .venv/bin/activate

# Install with dev dependencies
uv pip install -e ".[dev]"

# Or install pytest directly
uv pip install pytest pytest-asyncio pytest-cov
```

#### 5. Coverage Report Not Generated

**Cause**: Missing `--cov-report` flag

**Fix**:
```bash
# Generate both terminal and HTML reports
pytest --cov=src --cov-report=html --cov-report=term

# Open HTML report
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
```

### Debug Mode

**Enable debug logging**:
```bash
# Edit .env
LOG_LEVEL=DEBUG

# Restart backend
docker-compose restart backend

# View debug logs
docker-compose logs -f backend
```

**Debug FastAPI**:
```bash
# Run backend with auto-reload and debug mode
uvicorn src.main:app --reload --log-level debug
```

### Getting Help

- **Documentation**: Check `docs/` and `specs/` folders
- **Logs**: Always check structured logs with correlation IDs
- **GitHub Issues**: Search existing issues or create new one
- **Tests**: Run specific tests to isolate problems

---

## Next Steps

### Phase 4: Production Readiness (Planned)

- [ ] Increase test coverage to 80%
- [ ] Add performance benchmarks (load testing)
- [ ] Implement Prometheus metrics endpoint
- [ ] Add GitHub Actions CI/CD pipeline
- [ ] Deploy to production environment
- [ ] Monitor error rates and latency

### Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) (if exists) for contribution guidelines.

### Additional Resources

- **Specs**: [specs/001-ai-test-generation/](../specs/001-ai-test-generation/)
- **LangGraph**: [docs/langgraph-implementation.md](./langgraph-implementation.md)
- **uv Setup**: [docs/uv-setup.md](./uv-setup.md)
- **GitHub API**: [PyGithub documentation](https://pygithub.readthedocs.io/)
- **FastAPI**: [FastAPI documentation](https://fastapi.tiangolo.com/)
- **LangGraph**: [LangGraph documentation](https://langchain-ai.github.io/langgraph/)

---

**Last Updated**: 2025-01-20 | **Phase 3**: 100% Complete | **Tests**: 90/91 passing
