# Implementation Plan: AI Test Case Generation System

**Branch**: `001-ai-test-generation` | **Date**: 2025-10-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-test-generation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build an AI-powered test case generation system that automatically creates test case PRs when GitHub issues are tagged with "generate-tests". The system receives webhooks via Cloudflare Tunnel, uses LangGraph for AI workflow orchestration, retrieves context from a vector database, and generates Markdown test cases. Includes a simple monitoring dashboard UI to display processing status, database contents, and generated test cases statistics.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (webhooks), LangGraph (AI workflow), Llama 3.2 (local server), PyGithub (GitHub operations)  
**Storage**: Qdrant/ChromaDB (vector database for embeddings), Redis (1-hour idempotency cache)  
**Testing**: pytest (unit tests), pytest-asyncio (async testing), httpx (API testing)  
**Target Platform**: Linux server (containerized with Docker)  
**Project Type**: web (backend API + simple frontend dashboard)  
**Performance Goals**: <10s webhook response, <2min end-to-end generation, 100 concurrent requests  
**Constraints**: <200ms p95 webhook latency, 5,000 char input limit, 30-day vector DB retention  
**Scale/Scope**: Single repository support, ~1000 issues/month, ~10k vector embeddings max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Required Compliance Gates** (from `.specify/memory/constitution.md`):

- [x] **Simplicity Gate**: Feature design avoids unnecessary complexity - System uses straightforward webhook → AI → PR workflow with minimal services (FastAPI, LangGraph, vector DB, cache)
- [x] **Testing Gate**: Test strategy defined (unit + integration tests planned) - pytest for all components, contract tests for GitHub API, integration tests for full workflow
- [x] **Modularity Gate**: Components are independent with clear interfaces - Webhook handler, Vector store, AI agent, GitHub client, Dashboard UI are separate modules
- [x] **Documentation Gate**: Documentation plan includes component READMEs - Each backend service and frontend component will have README with API docs and usage examples
- [x] **Story Independence Gate**: User stories are independently testable - P1 (core generation), P2 (context retrieval), P3 (security) can be tested and deployed independently

**Justification for Any Complexity** (if applicable):
No unjustified complexity. The architecture follows a linear workflow (webhook → context → AI → Git operations → dashboard update) with clear separation of concerns. Vector database and cache are necessary for functional requirements (FR-004, FR-017).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application (backend API + frontend dashboard)
backend/
├── src/
│   ├── models/           # Data models (WebhookEvent, TestCase, AgentState)
│   ├── services/
│   │   ├── webhook/      # GitHub webhook handler
│   │   ├── vector/       # Vector DB operations
│   │   ├── ai/           # LangGraph agent workflow
│   │   └── github/       # GitHub API client (PR, branch, comments)
│   ├── api/              # FastAPI routes
│   │   ├── webhooks.py   # POST /webhooks/github
│   │   └── dashboard.py  # GET /api/stats, /api/issues, /api/test-cases
│   ├── core/
│   │   ├── config.py     # Configuration management
│   │   ├── logging.py    # Structured logging with correlation IDs
│   │   └── cache.py      # Redis idempotency cache
│   └── main.py           # FastAPI app entry point
└── tests/
    ├── unit/             # Unit tests for each service
    ├── integration/      # Full workflow tests
    └── contract/         # GitHub API contract tests

frontend/
├── src/
│   ├── components/
│   │   ├── ProcessingStats.tsx   # Real-time processing statistics
│   │   ├── IssueList.tsx         # GitHub issues with "generate-tests" tag
│   │   ├── TestCaseGrid.tsx      # Generated test cases display
│   │   └── DatabaseStatus.tsx    # Vector DB and cache status
│   ├── pages/
│   │   └── Dashboard.tsx         # Main monitoring dashboard
│   ├── services/
│   │   └── api.ts                # Backend API client
│   └── App.tsx                   # React app entry point
└── tests/
    └── components/       # Component tests

docker/
├── Dockerfile.backend    # Backend container
├── Dockerfile.frontend   # Frontend container
└── docker-compose.yml    # Full stack deployment

.github/
└── workflows/
    └── ci.yml            # CI/CD pipeline (tests, build, deploy)
```

**Structure Decision**: Selected web application structure (backend + frontend) because the system requires:

1. Backend API for webhook handling and AI processing
2. Simple frontend dashboard for monitoring (user requirement)
3. Separation enables independent scaling and testing of API vs UI

## Complexity Tracking

> **No violations detected.** All Constitution Check gates passed. The architecture follows simplicity principles with minimal dependencies and clear separation of concerns.

---

## Phase Completion Summary

### ✅ Phase 0: Research Complete

**Output**: [research.md](./research.md)

**Decisions Made**:

- Vector DB: ChromaDB (MVP), Qdrant (production scale)
- AI Workflow: LangGraph + Llama 3.2 (local server)
- Embeddings: sentence-transformers (local, all-MiniLM-L6-v2)
- LLM Inference: Ollama (recommended for simplicity)
- Cache: Redis with 1-hour TTL
- Web Framework: FastAPI (async, auto-docs)
- Frontend: React + TypeScript + TailwindCSS
- Testing: pytest with AAA pattern
- Deployment: Docker Compose (MVP), Kubernetes (production)
- Test Format: Markdown with YAML frontmatter

**All NEEDS CLARIFICATION resolved**: ✅

### ✅ Phase 1: Design Complete

**Outputs**:

- [data-model.md](./data-model.md) - 8 core entities with relationships and state machines
- [contracts/openapi.yaml](./contracts/openapi.yaml) - REST API specification
- [quickstart.md](./quickstart.md) - Setup and deployment guide
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md) - Updated with technologies

**Entities Defined**: WebhookEvent, ProcessingJob, VectorEmbedding, TestCaseDocument, GitHubPullRequest, AgentState, IdempotencyCache, DashboardMetrics

**API Endpoints**: 4 endpoints (webhook, stats, issues, test-cases, health)

**Agent Context Updated**: ✅ Technologies added to GitHub Copilot instructions

### ✅ Constitution Re-Check Post-Design

All gates remain PASSED after detailed design:

- **Simplicity**: Architecture uses 4 services (backend, frontend, ChromaDB, Redis), no over-engineering
- **Testing**: Unit tests for each service (80% coverage), integration tests for workflows (70% coverage), contract tests for external APIs
- **Modularity**: 5 backend services (webhook, vector, ai, github, cache), 4 frontend components, clear interfaces defined in OpenAPI spec
- **Documentation**: 4 planning docs created, component READMEs planned in project structure, API contracts documented
- **Story Independence**: P1 (webhook→PR) can ship alone, P2 (context retrieval) adds quality, P3 (security) hardens production

**Validation**: ✅ Zero linting errors in all generated files

---

## Next Steps

**Command**: `/speckit.tasks`

**Purpose**: Generate task breakdown with:

- Phase organization by user story (P1, P2, P3)
- Dependency-ordered tasks within each phase
- Test-first tasks (write tests before implementation)
- Parallel execution opportunities marked with [P] flag
- Estimated effort and acceptance criteria per task

**Estimated Tasks**: ~30-40 tasks across 4 phases (Setup, P1 MVP, P2 Context, P3 Security)

**Ready for Implementation**: ✅ All planning artifacts complete
