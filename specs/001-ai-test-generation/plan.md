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

## Performance Requirements and Constraints

### API Response Time Constraints

- **Webhook Response**: <200ms p95 latency from request receipt to 202 Accepted response (per spec constraint)
- **Background Processing**: <10s for async processing to start after webhook queuing (per performance goal)
- **Vector Database Query**: <500ms p95 for similarity search with k=5 results (per FR-028)
- **GitHub API Operations**: <2s per operation (branch creation, commit, PR creation) within rate limits
- **End-to-End Generation**: <2min p95 from webhook receipt to PR creation (per performance goal)
- **Dashboard Data Refresh**: 5-second intervals for real-time statistics (per FR-036)
- **Health Check Endpoint**: <50ms for `/health` endpoint response

### Resource Limits (per Container)

- **Backend Service Memory**: 512MB limit, 256MB reservation (per FR-029)
- **Frontend Service Memory**: 256MB limit, 128MB reservation (per FR-029)
- **AI Service Memory**: 4GB limit (Llama 3.2 model), 2GB reservation
- **Vector DB Memory**: 2GB limit, 1GB reservation (10k embeddings × 384 dimensions)
- **Redis Cache Memory**: 256MB limit, 128MB reservation (1-hour idempotency keys)
- **CPU Allocation**: 1 vCPU per service with burstable capacity to 2 vCPU during peak load
- **Disk I/O**: 100 IOPS minimum for vector DB storage (SSD required)

### Throughput and Concurrency Limits

- **Concurrent Webhook Requests**: 100 simultaneous requests without request dropping (per SC-002, performance goal)
- **Queue Depth**: Maximum 1000 pending jobs; reject new webhooks with 503 Service Unavailable if exceeded
- **AI Generation Throughput**: 3.3 requests/sec sustained (100 concurrent / 30s avg generation time)
- **Vector DB Query Rate**: 20 queries/sec sustained (5 concurrent AI jobs × 4 context lookups each)
- **GitHub API Rate Limit**: 5000 requests/hour per OAuth token (GitHub standard); system uses ~6 requests per PR (branch, commit, PR, label, comment, update)
- **Repository Rate Limit**: 100 webhooks/min per repository to prevent abuse (per FR-020)
- **Dashboard API**: 50 requests/sec for stats endpoint (expected 10 users × 0.2 Hz refresh)

### Connection Pool Sizing

- **Database Connections**: 10 connections to ChromaDB (5 for writes, 5 for queries)
- **Redis Connections**: 5 connections for cache operations (get, set, delete)
- **GitHub API Connections**: 5 connections with connection pooling (keep-alive enabled)
- **HTTP Client Pool**: 20 connections total for all outbound requests

### Input and Output Size Constraints

- **Issue Body Truncation**: 5,000 characters maximum input (per spec constraint); truncate with warning if exceeded
- **Test Case Output Size**: ~10KB typical Markdown document (5 scenarios × ~2KB each)
- **Vector Embedding Size**: 384 dimensions (all-MiniLM-L6-v2 model) × 4 bytes = 1.5KB per embedding
- **PR Description Length**: 2,000 characters maximum (GitHub limit); truncate summary if needed
- **Log Message Size**: 1KB maximum per structured log entry; truncate stack traces to 500 chars

### Retention and Cleanup Policies

- **Vector DB Retention**: 30 days for test case embeddings (per A10 assumption; configurable via `VECTOR_DB_RETENTION_DAYS`)
- **Orphaned Branch Cleanup**: >7 days old branches with no active PR (per FR-025; daily cron at 2 AM UTC)
- **Idempotency Cache TTL**: 1 hour for duplicate webhook detection (per FR-017; Redis expiration)
- **Log Retention**: 30 days with compression (per FR-035; configurable retention policy)
- **Processing Job History**: 90 days for completed/failed jobs; permanent retention for SUCCEEDED jobs referenced by PRs

### Scaling and Load Testing Targets

- **Load Test Scenario**: 100 concurrent webhooks arriving within 10-second window (burst test)
- **Soak Test Duration**: 8-hour continuous load at 50% capacity (50 concurrent requests) to detect memory leaks
- **Stress Test Target**: 150% of concurrent limit (150 requests) to validate graceful degradation (503 responses, no crashes)
- **Spike Test**: 0 → 100 → 0 requests in 1 minute to validate autoscaling response time
- **Success Criteria**: <10% timeout rate (E301) during load test, zero crashes during soak test, <5s recovery after spike test

### Monitoring and Alerting Thresholds

- **Error Rate Alert**: >5% error rate in any 5-minute window (per FR-033)
- **Latency Alert**: p95 latency >2× target for 3 consecutive minutes (vector DB: >1s, webhook: >400ms)
- **Queue Depth Alert**: >50 pending jobs for >10 minutes (indicates backlog, trigger horizontal scaling)
- **Resource Utilization Alert**: >80% memory or CPU for >5 minutes (risk of OOM kill or throttling)
- **Storage Alert**: Vector DB storage >8GB (approaching 10GB limit per A10; trigger retention adjustment)
- **Rate Limit Alert**: GitHub API remaining quota <500 requests (10% of hourly limit)

### Performance Degradation Handling

- **Vector DB Unavailable**: Proceed without context (per Edge Cases §5); accept 10-15% quality drop, log warning E201
- **AI Service Timeout**: 3 retries with exponential backoff (5s, 15s, 45s per Edge Cases §7); mark FAILED if exhausted
- **GitHub API Rate Limit**: Wait 60s before retry (per Edge Cases §3); queue depth increases during wait period
- **High Queue Depth**: Return 202 Accepted immediately, extend processing time from <2min to <5min during peak
- **Memory Pressure**: Trigger garbage collection, reduce vector DB cache size, alert if >90% memory used

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
