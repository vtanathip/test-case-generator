# AI Test Case Generator

**AI-powered test case generation system using GitHub webhooks, LangGraph, and Llama 3.2**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 🚀 Overview

Automatically generate comprehensive test cases from GitHub issues using local AI. When an issue is labeled with `generate-tests`, the system:

1. **Receives** GitHub webhook event
2. **Retrieves** similar test cases from vector database
3. **Generates** test case documentation using Llama 3.2
4. **Commits** Markdown file to new branch
5. **Creates** pull request with generated tests

**Key Features:**

- 🤖 **Local AI** - Llama 3.2 via Ollama (no external API costs)
- ⚡ **Fast** - Webhook response <200ms, end-to-end <2min
- 🔒 **Secure** - HMAC signature verification, secret scanning
- 📊 **Observable** - Structured logging, metrics dashboard
- 🔄 **Reliable** - Exponential backoff retries, idempotency cache
- 🎯 **Context-aware** - Vector similarity search for relevant examples

## 📋 Prerequisites

- **Docker Desktop** 24.0+ with Docker Compose 2.20+
- **GPU** (recommended): NVIDIA GPU with 8GB+ VRAM for Llama 3.2 11B
  - *CPU-only*: Use `llama3.2:3b` model (5-10x slower)
- **GitHub** account with repository access
- **Cloudflare** account for tunnel setup

## 🏃 Quick Start

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/owner/test-case-generator.git
cd test-case-generator

# Copy environment template
cp .env.example .env

# Edit .env with your credentials (see Configuration section)
```

### 2. Install and Start Ollama

```bash
# Windows
winget install Ollama.Ollama

# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull Llama 3.2 model (~2GB)
ollama pull llama3.2:latest
```

### 3. Start Docker Services

```bash
# Start backend, frontend, ChromaDB, Redis
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Configure GitHub Webhook

1. Go to **GitHub repository → Settings → Webhooks → Add webhook**
2. **Payload URL**: `https://your-tunnel-domain.trycloudflare.com/webhooks/github`
3. **Content type**: `application/json`
4. **Secret**: Value from `GITHUB_WEBHOOK_SECRET` in `.env`
5. **Events**: Select "Issues" only
6. **Active**: ✓ Enabled
7. **Save webhook**

### 4. Create Test Issue

Create a GitHub issue with:
- **Label**: `generate-tests`
- **Title**: "Add user authentication feature"
- **Body**: "Implement OAuth2 authentication with Google provider. Support login, logout, and token refresh."

Within 2 minutes, check:
- Dashboard at `http://localhost:3000`
- New PR in your repository with generated test cases

## 🏗️ Architecture

```text
GitHub Webhook
     ↓
FastAPI Backend (Python 3.11)
     ↓
LangGraph Workflow:
  1. Validate signature
  2. Check idempotency cache (Redis)
  3. Query vector DB for context (ChromaDB)
  4. Generate test cases (Llama 3.2 via Ollama)
  5. Create branch & commit
  6. Open pull request
     ↓
React Dashboard (TypeScript)
```

**Tech Stack:**

- **Backend**: Python 3.11, FastAPI, LangGraph, Ollama (local), PyGithub
- **Storage**: ChromaDB (vector DB), Redis (cache)
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS
- **Infrastructure**: Docker Compose (4 services)
- **AI**: Llama 3.2 running locally via Ollama

## ⚙️ Configuration

### Required Environment Variables

Create a `.env` file in the project root with these values:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx          # Personal access token (repo write permission required)
GITHUB_WEBHOOK_SECRET=your_secret_here  # Webhook signature secret (match GitHub webhook config)
GITHUB_REPO=owner/repo                  # Repository full name (e.g., vtanathip/test-case-generator)

# AI Configuration (Local Ollama)
LLAMA_MODEL=llama3.2:latest             # Model variant (llama3.2:3b for faster/smaller, llama3.2:latest for better quality)
OLLAMA_HOST=http://host.docker.internal:11434  # IMPORTANT: Use host.docker.internal, NOT localhost
OLLAMA_TIMEOUT=120                      # Generation timeout in seconds

# Vector Database (ChromaDB)
CHROMADB_HOST=chromadb                  # Docker service name (don't change)
CHROMADB_PORT=8000                      # ChromaDB port
CHROMADB_COLLECTION=test_cases          # Collection name for test case embeddings
CHROMADB_EMBEDDING_MODEL=all-MiniLM-L6-v2  # SentenceTransformer model for embeddings

# Cache (Redis)
REDIS_HOST=redis                        # Docker service name (don't change)
REDIS_PORT=6379                         # Redis port
REDIS_DB=0                              # Redis database number
REDIS_IDEMPOTENCY_TTL=3600              # Idempotency cache TTL (1 hour)

# Backend Configuration
BACKEND_HOST=0.0.0.0                    # Listen on all interfaces
BACKEND_PORT=8000                       # Backend API port
LOG_LEVEL=INFO                          # Logging level (DEBUG, INFO, WARNING, ERROR)

# Frontend Configuration  
FRONTEND_PORT=3000                      # Frontend dashboard port
VITE_API_URL=http://localhost:8000      # Backend API URL for frontend

# GitHub API
GITHUB_API_TIMEOUT=30                   # GitHub API timeout in seconds
```

### Critical Configuration Notes

1. **OLLAMA_HOST Must Use `host.docker.internal`**
   ```bash
   # ✅ CORRECT - Allows Docker container to reach host Ollama
   OLLAMA_HOST=http://host.docker.internal:11434
   
   # ❌ WRONG - Won't work from inside Docker container
   OLLAMA_HOST=http://localhost:11434
   ```

2. **GitHub Token Permissions**
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate new token (classic) with:
     - ✅ `repo` (Full control of private repositories)
     - ✅ `workflow` (Update GitHub Action workflows) - optional
   - Copy token and add to `.env` as `GITHUB_TOKEN`

3. **Webhook Secret**
   - Generate a random secret: `openssl rand -hex 32`
   - Add same secret to:
     - `.env` as `GITHUB_WEBHOOK_SECRET`
     - GitHub webhook configuration

4. **Model Selection**
   ```bash
   # For better quality (requires 8GB RAM):
   LLAMA_MODEL=llama3.2:latest  # ~2GB model download
   
   # For faster generation (requires 2GB RAM):
   LLAMA_MODEL=llama3.2:3b      # ~1.3GB model download
   ```

### Environment Template

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Then edit `.env` with your actual credentials.

## 🛠️ Development

### Backend Development

```bash
cd backend

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Lint code
ruff check .

# Start dev server
uvicorn src.main:app --reload
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Run tests
npm run test

# Lint code
npm run lint
```

### Project Structure

```text
test-case-generator/
├── backend/
│   ├── src/
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Business logic
│   │   ├── api/             # FastAPI routes
│   │   └── core/            # Config, logging, clients
│   ├── tests/               # Backend tests
│   └── pyproject.toml       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Route pages
│   │   └── services/        # API client
│   ├── package.json         # Node dependencies
│   └── vite.config.ts       # Vite configuration
├── docker/
│   ├── docker-compose.yml   # Service orchestration
│   ├── Dockerfile.backend   # Backend container
│   └── Dockerfile.frontend  # Frontend container
├── specs/                   # Feature specifications
├── .env.example             # Environment template
└── README.md                # This file
```

## 📊 Performance

- **Webhook Response**: <200ms p95
- **Vector Query**: <500ms p95
- **End-to-End**: <2min p95 (webhook → PR)
- **Throughput**: 100 concurrent webhooks, 3.3 AI requests/sec
- **Resource Limits**: 512MB backend, 4GB AI service, 2GB vector DB

## 🔒 Security

- ✅ HMAC-SHA256 webhook signature verification
- ✅ GitHub token permissions (repo write only)
- ✅ Secret scanning in committed files
- ✅ Rate limiting (100 concurrent requests)
- ✅ Input validation (Pydantic models)
- ✅ CORS configuration

## 📝 Testing

### Backend Tests

```bash
# Backend tests (90/91 passing)
cd backend
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/contract/      # Contract tests
```

### End-to-End Testing

For complete system validation with real GitHub issues:

**See: [TEST_CASES.md](docs/TEST_CASES.md)**

Includes 3 comprehensive test scenarios:
1. **User Authentication Feature** - OAuth2 test case generation
2. **REST API Endpoint** - API testing with error codes
3. **Database Migration** - Schema change test cases

Each test case includes:
- Complete issue templates (copy-paste ready)
- Expected log sequences
- Validation steps
- Success criteria
- Performance benchmarks

### Frontend Tests

```bash
# Frontend tests
cd frontend
npm run test:coverage
```

## 🐛 Troubleshooting

### Quick Checks

**Webhook not received?**

- Verify issue has `generate-tests` label
- Check backend logs: `docker-compose logs backend | Select-String "webhook_received"`
- Confirm GitHub webhook is active in repository settings

**AI generation slow or failing?**

- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Verify model downloaded: `ollama list` (should show llama3.2:latest)
- Use smaller model for faster generation: `LLAMA_MODEL=llama3.2:3b`

**Services not starting?**

- Check all containers: `docker-compose ps` (all should show "Up")
- View specific service logs: `docker-compose logs [service-name]`
- Restart services: `docker-compose restart`

**Code changes not applied?**

- You MUST rebuild Docker image (restart alone won't work):
  ```bash
  docker-compose build backend
  docker-compose up -d backend
  ```

### Complete Troubleshooting Guide

For detailed troubleshooting including:
- ✅ System health checks
- ✅ Error code reference (E101-E404)
- ✅ Step-by-step diagnostics
- ✅ Common issues and solutions
- ✅ Performance optimization

**See: [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**

## 📚 Documentation

### Getting Started

| Document | Description | When to Read |
|----------|-------------|--------------|
| [README.md](README.md) | Project overview and quick start | **START HERE** - First time setup |
| [QUICKSTART_GUIDE.md](docs/QUICKSTART_GUIDE.md) | Step-by-step installation | Setting up for the first time |
| [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Development workflow and testing | Contributing code or running tests |

### Operational Guides

| Document | Description | When to Read |
|----------|-------------|--------------|
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and solutions | **Something not working** |
| [TEST_CASES.md](docs/TEST_CASES.md) | 3 end-to-end test scenarios | Validating system functionality |
| [uv-setup.md](docs/uv-setup.md) | Python environment with uv | Setting up local development |

### Technical Documentation

| Document | Description | When to Read |
|----------|-------------|--------------|
| [langgraph-implementation.md](docs/langgraph-implementation.md) | AI workflow architecture | Understanding LangGraph state machine |
| [DOCUMENTATION_STANDARDS.md](docs/DOCUMENTATION_STANDARDS.md) | Documentation guidelines | Writing or updating docs |
| [DOCUMENTATION_AUDIT_REPORT.md](docs/DOCUMENTATION_AUDIT_REPORT.md) | Documentation review results | Checking doc quality |

### Feature Specifications

| Document | Description | When to Read |
|----------|-------------|--------------|
| [spec.md](specs/001-ai-test-generation/spec.md) | Feature requirements and success criteria | Understanding requirements |
| [plan.md](specs/001-ai-test-generation/plan.md) | Technical implementation plan | Implementation details |
| [data-model.md](specs/001-ai-test-generation/data-model.md) | Entity definitions and state machines | Database schema and models |
| [error-catalog.md](specs/001-ai-test-generation/error-catalog.md) | Error codes and recovery strategies | Debugging error codes |
| [contracts/openapi.yaml](specs/001-ai-test-generation/contracts/openapi.yaml) | OpenAPI specification | API contract details |

### Quick Reference

| Scenario | Read This |
|----------|-----------|
| 🚀 **First time user** | README → QUICKSTART_GUIDE → TEST_CASES |
| � **Something broken** | TROUBLESHOOTING → Check logs → Error catalog |
| 👨‍💻 **Contributing code** | DEVELOPER_GUIDE → DOCUMENTATION_STANDARDS |
| 🏗️ **Understanding architecture** | langgraph-implementation → spec.md → plan.md |
| ✅ **Testing changes** | TEST_CASES → DEVELOPER_GUIDE (testing section) |
| 📝 **Writing documentation** | DOCUMENTATION_STANDARDS → Existing docs as examples |

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open pull request

## 🙏 Acknowledgments

- **Llama 3.2** by Meta AI
- **Ollama** for local LLM serving
- **LangGraph** for workflow orchestration
- **FastAPI** for high-performance backend


A modular, test-driven framework for generating comprehensive test cases across multiple testing frameworks and languages.

## Overview

The Test Case Generator project provides a robust, extensible system for automatically generating test cases based on code analysis, specifications, and design documents. Built with simplicity, modularity, and testability at its core, this tool helps development teams maintain high code quality through automated test generation.

## Architecture

### High-Level Design

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Test Case Generator                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Parser     │  │  Analyzer    │  │  Generator   │          │
│  │   Module     │→ │   Module     │→ │   Module     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         ↓                 ↓                  ↓                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Input Models │  │ Test Models  │  │ Output       │          │
│  │ (Code, Spec) │  │ (Scenarios)  │  │ (Test Files) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Validation & Verification Engine             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

- **Parser Module**: Extracts code structure, specifications, and design artifacts
- **Analyzer Module**: Identifies test scenarios, edge cases, and coverage gaps
- **Generator Module**: Creates test cases in target framework syntax
- **Validation Engine**: Ensures generated tests are syntactically correct and comprehensive

## Project Structure

```text
test-case-generator/
├── src/                          # Source code
│   ├── parser/                   # Code and spec parsing
│   │   └── README.md
│   ├── analyzer/                 # Test scenario analysis
│   │   └── README.md
│   ├── generator/                # Test case generation
│   │   └── README.md
│   ├── validator/                # Output validation
│   │   └── README.md
│   └── models/                   # Shared data models
│       └── README.md
├── tests/                        # Test suites
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── contract/                 # Contract tests
├── docs/                         # Documentation
│   ├── architecture.md
│   ├── api-reference.md
│   └── examples/
├── specs/                        # Feature specifications
│   └── [feature-id]/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── .specify/                     # Project governance
│   ├── memory/
│   │   └── constitution.md       # Project constitution
│   └── templates/                # Document templates
└── README.md                     # This file
```

## Core Principles

This project follows five non-negotiable core principles defined in our [Constitution](./.specify/memory/constitution.md):

1. **Simplicity First**: All logic must be simple, concise, and avoid unnecessary complexity
2. **Test-First Development**: TDD is mandatory with comprehensive unit and integration tests
3. **Modular Architecture**: Features built as independent, reusable components
4. **Comprehensive Documentation**: Every component has its own README with API docs and examples
5. **Incremental Delivery**: Features delivered as independently testable user stories

## Getting Started

### Prerequisites

- [To be defined based on technology stack choice]
- Testing framework: [TBD]
- Build tools: [TBD]

### Installation

```bash
# Clone the repository
git clone https://github.com/vtanathip/test-case-generator.git
cd test-case-generator

# Install dependencies
[Installation commands to be added]

# Run tests to verify installation
[Test commands to be added]
```

### Quick Start

```bash
# Example usage (to be implemented)
test-case-generator --input ./source-code --output ./tests --framework jest

# Run with specification input
test-case-generator --spec ./specs/feature/spec.md --output ./tests
```

## Development Workflow

### 1. Feature Development

All features follow the SpecKit workflow:

```bash
# Create feature specification
/speckit.specify "Feature description"

# Generate implementation plan
/speckit.plan

# Break down into tasks
/speckit.tasks

# Implement following TDD
# - Write tests first
# - Ensure they fail
# - Implement feature
# - Verify tests pass
# - Refactor
```

### 2. Constitution Compliance

Before merging, all features must pass:

- ✅ **Simplicity Gate**: No unnecessary complexity
- ✅ **Testing Gate**: 80%+ unit test coverage, 70%+ integration coverage
- ✅ **Modularity Gate**: Independent, reusable components
- ✅ **Documentation Gate**: Complete README and API docs, **synchronized with code changes**
- ✅ **Story Independence Gate**: Independently testable user stories

### 3. Documentation Synchronization (CRITICAL)

**Every code change MUST include documentation updates in the same commit/PR:**

| Change Type | Documents to Update |
|-------------|---------------------|
| New Feature | Component README, Main README, API docs, Examples |
| Bug Fix | Inline comments, Troubleshooting, Changelog |
| Refactoring | API docs, README, Architecture diagrams |
| Breaking Change | ALL affected docs, Migration guide |

See [Documentation Synchronization Standard](./.specify/memory/constitution.md#documentation-synchronization-standard-non-negotiable) for complete requirements.

### 4. Code Review Checklist

- [ ] Code follows YAGNI principles
- [ ] All functions have unit tests
- [ ] Integration tests cover component boundaries
- [ ] Public APIs are documented
- [ ] **Component README is updated** ✨
- [ ] **Main README updated (if architectural changes)** ✨
- [ ] **API documentation updated** ✨
- [ ] **Code comments updated** ✨
- [ ] **Examples updated** ✨
- [ ] **Changelog entry added** ✨
- [ ] Examples are runnable and tested
- [ ] No circular dependencies

> ✨ = Documentation Synchronization Requirements

## Testing

### Running Tests

```bash
# Run all tests
[Test command TBD]

# Run unit tests only
[Unit test command TBD]

# Run integration tests
[Integration test command TBD]

# Check test coverage
[Coverage command TBD]
```

### Test Organization

- **Unit Tests** (`tests/unit/`): Test individual functions in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions
- **Contract Tests** (`tests/contract/`): Verify module interfaces

## Documentation

### Component Documentation

Each major component has its own README:

- [Parser Module](./src/parser/README.md) - Code and specification parsing
- [Analyzer Module](./src/analyzer/README.md) - Test scenario analysis
- [Generator Module](./src/generator/README.md) - Test case generation
- [Validator Module](./src/validator/README.md) - Output validation

### Architecture Documentation

- [Architecture Overview](./docs/architecture.md)
- [API Reference](./docs/api-reference.md)
- [Examples](./docs/examples/)

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Read the Constitution**: Familiarize yourself with [our principles](./.specify/memory/constitution.md)
2. **Create a Feature Spec**: Use `/speckit.specify` for new features
3. **Follow TDD**: Write tests first, always
4. **Document Everything**: Update READMEs and API docs
5. **Keep It Simple**: Avoid unnecessary complexity
6. **Make It Modular**: Build independent, reusable components

### Pull Request Process

1. Create a feature branch from `main`
2. Follow the TDD workflow
3. Ensure all tests pass
4. Update documentation
5. Pass all constitution compliance gates
6. Submit PR with clear description

## Project Governance

This project is governed by our [Constitution](./.specify/memory/constitution.md), which defines:

- Core principles (non-negotiable)
- Development workflow requirements
- Quality standards and gates
- Amendment process

All contributions must comply with constitutional requirements.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Repository**: [github.com/vtanathip/test-case-generator](https://github.com/vtanathip/test-case-generator)
- **Issues**: [GitHub Issues](https://github.com/vtanathip/test-case-generator/issues)

## Status

**Current Version**: Pre-alpha  
**Constitution Version**: 1.1.0 (Documentation Synchronization Standard Added)

- ✅ Project constitution established and amended
- ✅ Documentation synchronization requirements defined
- ⏳ Core architecture design in progress
- ⏳ Component implementation pending
- ⏳ Initial release planning

---

**Last Updated**: 2025-10-25
