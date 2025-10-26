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

### 2. Start Services

```bash
# Start all services (backend, frontend, ChromaDB, Redis, Ollama)
docker-compose up -d

# Pull Llama 3.2 model (first time only, 5-10 minutes)
docker-compose exec ollama ollama pull llama3.2:11b

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

- **Backend**: Python 3.11, FastAPI, LangGraph, Ollama, PyGithub
- **Storage**: ChromaDB (vector DB), Redis (cache)
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS
- **Infrastructure**: Docker Compose (5 services)
- **AI**: Llama 3.2 (11B or 90B) running locally

## ⚙️ Configuration

### Required Environment Variables

Edit `.env` file:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx          # Personal access token (repo write)
GITHUB_WEBHOOK_SECRET=your_secret_here  # Webhook signature secret
GITHUB_REPO=owner/repo                  # Repository full name

# Llama Configuration
LLAMA_MODEL=llama3.2:11b                # Model variant (3b, 11b, 90b)
OLLAMA_HOST=http://ollama:11434         # Ollama server URL

# ChromaDB Configuration
CHROMADB_HOST=chromadb                  # ChromaDB hostname
CHROMADB_COLLECTION=test_cases          # Collection name

# Redis Configuration
REDIS_HOST=redis                        # Redis hostname
REDIS_IDEMPOTENCY_TTL=3600              # Cache TTL (1 hour)

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=xxx             # Tunnel token
```

See `.env.example` for complete configuration.

## 🛠️ Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

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

```bash
# Backend tests (80% coverage target)
cd backend
pytest --cov=src --cov-report=html

# Frontend tests
cd frontend
npm run test:coverage
```

## 🐛 Troubleshooting

**Issue: Webhook not received**
- Verify Cloudflare tunnel is running: `docker-compose logs cloudflare-tunnel`
- Check webhook secret matches `.env` value
- Confirm issue has `generate-tests` label

**Issue: Slow AI generation**
- Check GPU availability: `docker-compose exec ollama nvidia-smi`
- Consider smaller model: `llama3.2:3b`
- Monitor resource usage: `docker stats`

**Issue: Vector DB empty**
- Seed initial test cases: See `specs/001-ai-test-generation/quickstart.md`
- Check ChromaDB logs: `docker-compose logs chromadb`

## 📚 Documentation

- **Specification**: [`specs/001-ai-test-generation/spec.md`](specs/001-ai-test-generation/spec.md)
- **Implementation Plan**: [`specs/001-ai-test-generation/plan.md`](specs/001-ai-test-generation/plan.md)
- **API Contract**: [`specs/001-ai-test-generation/contracts/openapi.yaml`](specs/001-ai-test-generation/contracts/openapi.yaml)
- **Data Model**: [`specs/001-ai-test-generation/data-model.md`](specs/001-ai-test-generation/data-model.md)
- **Error Catalog**: [`specs/001-ai-test-generation/error-catalog.md`](specs/001-ai-test-generation/error-catalog.md)

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
