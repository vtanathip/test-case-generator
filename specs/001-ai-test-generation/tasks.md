---
description: "Task list for AI Test Case Generation System implementation"
---

# Tasks: AI Test Case Generation System

**Input**: Design documents from `/specs/001-ai-test-generation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅

**Tests**: Test tasks included based on constitution requirement (80% unit coverage, 70% integration coverage)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Per plan.md, this is a web application with:

- Backend: `backend/src/`, `backend/tests/`
- Frontend: `frontend/src/`, `frontend/tests/`
- Docker: `docker/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure per plan.md (backend/, frontend/, docker/, .github/workflows/)
- [ ] T002 Initialize Python 3.11+ backend with FastAPI in backend/pyproject.toml
- [ ] T003 [P] Initialize React + TypeScript frontend with Vite in frontend/package.json
- [ ] T004 [P] Configure Python linting (ruff) and formatting (black) in backend/pyproject.toml
- [ ] T005 [P] Configure TypeScript linting (ESLint) and formatting (Prettier) in frontend/.eslintrc.json
- [ ] T006 Create .env.example file with all required environment variables from quickstart.md
- [ ] T007 Create README.md at repository root with project overview and setup links

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Setup Docker Compose configuration in docker/docker-compose.yml (5 services: backend, frontend, ollama, chromadb, redis)
- [ ] T009 Create Dockerfile for backend in docker/Dockerfile.backend (Python 3.11, FastAPI, dependencies)
- [ ] T010 [P] Create Dockerfile for frontend in docker/Dockerfile.frontend (Node.js, Vite build)
- [ ] T011 [P] Configure Redis connection and idempotency cache client in backend/src/core/cache.py
- [ ] T012 [P] Configure ChromaDB connection and client in backend/src/core/vector_db.py
- [ ] T013 [P] Setup Ollama client for Llama 3.2 inference in backend/src/core/llm_client.py
- [ ] T014 Configure structured logging with correlation IDs (structlog) in backend/src/core/logging.py
- [ ] T015 Create configuration management system in backend/src/core/config.py (load from env vars)
- [ ] T016 Setup FastAPI application factory in backend/src/main.py with CORS, error handlers
- [ ] T017 Create base exception classes in backend/src/core/exceptions.py
- [ ] T018 [P] Create backend health check endpoint in backend/src/api/health.py (GET /api/health)
- [ ] T019 [P] Setup GitHub Actions CI workflow in .github/workflows/ci.yml (lint, test, build)
- [ ] T020 Install and configure sentence-transformers for local embeddings in backend/src/core/embeddings.py
- [ ] T021 [P] Setup PyGithub client configuration in backend/src/core/github_client.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Test Case Generation from GitHub Issue (Priority: P1) 🎯 MVP

**Goal**: Implement core webhook → AI → PR workflow that delivers automated test case generation

**Independent Test**: Create a GitHub issue with "generate-tests" tag, verify webhook triggers, and confirm PR with test cases is created within 2 minutes

### Tests for User Story 1 (Write FIRST, ensure they FAIL) ⚠️

- [ ] T022 [P] [US1] Unit test for WebhookEvent model validation in backend/tests/unit/models/test_webhook_event.py
- [ ] T023 [P] [US1] Unit test for ProcessingJob state machine in backend/tests/unit/models/test_processing_job.py
- [ ] T024 [P] [US1] Unit test for TestCaseDocument generation in backend/tests/unit/models/test_test_case_document.py
- [ ] T025 [P] [US1] Unit test for webhook signature validation in backend/tests/unit/services/test_webhook_service.py
- [ ] T026 [P] [US1] Unit test for LangGraph agent workflow in backend/tests/unit/services/test_ai_service.py
- [ ] T027 [P] [US1] Unit test for GitHub operations (branch, commit, PR) in backend/tests/unit/services/test_github_service.py
- [ ] T028 [US1] Integration test for full webhook → PR workflow in backend/tests/integration/test_end_to_end.py
- [ ] T029 [US1] Contract test for GitHub API interactions in backend/tests/contract/test_github_api.py

### Data Models for User Story 1

- [ ] T030 [P] [US1] Create WebhookEvent model in backend/src/models/webhook_event.py (8 attributes per data-model.md)
- [ ] T031 [P] [US1] Create ProcessingJob model in backend/src/models/processing_job.py (5-state state machine)
- [ ] T032 [P] [US1] Create TestCaseDocument model in backend/src/models/test_case_document.py (Markdown with metadata)
- [ ] T033 [P] [US1] Create GitHubPullRequest model in backend/src/models/github_pr.py (PR state tracking)
- [ ] T034 [P] [US1] Create AgentState model in backend/src/models/agent_state.py (LangGraph 6-stage workflow)

### Services for User Story 1

- [ ] T035 [US1] Implement WebhookService in backend/src/services/webhook/webhook_service.py
  - Parse GitHub webhook payload
  - Validate signature (HMAC-SHA256)
  - Check for "generate-tests" tag (FR-002)
  - Create WebhookEvent and ProcessingJob records
  - Queue background task
- [ ] T036 [US1] Implement AIService with LangGraph workflow in backend/src/services/ai/ai_service.py
  - Define 6 stages: RECEIVE, RETRIEVE, GENERATE, COMMIT, CREATE_PR, FINALIZE
  - Integrate Ollama client for Llama 3.2 inference
  - Implement exponential backoff retry logic (3 retries: 5s, 15s, 45s)
  - Handle 120s timeout for local inference
  - Generate test cases in Markdown format per template
- [ ] T037 [US1] Implement GitHubService in backend/src/services/github/github_service.py
  - Create branch with pattern "test-cases/issue-{number}" (FR-007)
  - Commit Markdown file to branch (FR-008)
  - Create pull request linking to issue (FR-009)
  - Add comment to issue with PR link (FR-010)
  - Add failure comment if generation fails (FR-011)
- [ ] T038 [US1] Create test case generation prompt template in backend/src/services/ai/prompts/test_case_template.py
  - Include issue title, body, and context
  - Define Markdown format structure
  - Include examples for few-shot learning

### API Endpoints for User Story 1

- [ ] T039 [US1] Implement POST /webhooks/github endpoint in backend/src/api/webhooks.py
  - Validate headers (X-GitHub-Event, X-Hub-Signature-256, X-GitHub-Delivery)
  - Return 202 Accepted with correlation_id
  - Handle 400 (invalid), 401 (signature fail), 409 (duplicate) errors
  - Background task dispatch to AIService

### Error Handling & Monitoring for User Story 1

- [ ] T040 [US1] Add structured logging for webhook processing in backend/src/services/webhook/webhook_service.py
  - Log with correlation_id at each stage
  - Log signature validation result
  - Log tag check result
- [ ] T041 [US1] Add structured logging for AI workflow in backend/src/services/ai/ai_service.py
  - Log stage transitions
  - Log retry attempts
  - Log LLM inference duration
  - Log token count if available
- [ ] T042 [US1] Add structured logging for GitHub operations in backend/src/services/github/github_service.py
  - Log branch creation
  - Log commit hash
  - Log PR number and URL
- [ ] T043 [US1] Create README.md in backend/src/models/ explaining data model relationships and state machines
- [ ] T044 [US1] Create README.md in backend/src/services/ explaining service architecture and workflow stages

**Checkpoint**: At this point, User Story 1 should be fully functional - webhook triggers test case generation and creates PR

---

## Phase 4: User Story 2 - Issue Content Analysis and Context Retrieval (Priority: P2)

**Goal**: Enhance test case quality by retrieving relevant historical test cases from vector database for context-aware generation

**Independent Test**: Create issues with similar content, verify that generated test cases reference or incorporate patterns from previous similar issues

### Tests for User Story 2 (Write FIRST, ensure they FAIL) ⚠️

- [ ] T045 [P] [US2] Unit test for VectorEmbedding model in backend/tests/unit/models/test_vector_embedding.py
- [ ] T046 [P] [US2] Unit test for vector similarity search in backend/tests/unit/services/test_vector_service.py
- [ ] T047 [P] [US2] Unit test for embedding generation with sentence-transformers in backend/tests/unit/services/test_embedding_service.py
- [ ] T048 [US2] Integration test for context retrieval workflow in backend/tests/integration/test_context_retrieval.py

### Data Models for User Story 2

- [ ] T049 [US2] Create VectorEmbedding model in backend/src/models/vector_embedding.py
  - 384-dim or 768-dim vector
  - 30-day TTL (expires_at)
  - Metadata (issue_number, labels, repository)

### Services for User Story 2

- [ ] T050 [US2] Implement EmbeddingService in backend/src/services/vector/embedding_service.py
  - Load sentence-transformers model (all-MiniLM-L6-v2)
  - Generate embeddings from text content
  - Handle 8000 char limit
- [ ] T051 [US2] Implement VectorService in backend/src/services/vector/vector_service.py
  - Store embeddings in ChromaDB with metadata
  - Query by similarity (cosine distance, top 5 results per FR-004)
  - Implement 30-day TTL cleanup job
  - Filter results by similarity threshold (>0.7 per SC-006)
- [ ] T052 [US2] Update AIService to integrate context retrieval in backend/src/services/ai/ai_service.py
  - Call VectorService during RETRIEVE stage
  - Include top 5 results in prompt context
  - Update prompt template to use context
  - Track context_sources in TestCaseDocument metadata
- [ ] T053 [US2] Implement background job for embedding storage in backend/src/services/vector/embedding_job.py
  - Trigger after successful PR creation
  - Split test case into sections
  - Generate embeddings for each section
  - Store in ChromaDB with metadata

### Monitoring for User Story 2

- [ ] T054 [US2] Add structured logging for vector operations in backend/src/services/vector/vector_service.py
  - Log similarity scores
  - Log result count
  - Log query duration
- [ ] T055 [US2] Add structured logging for embedding generation in backend/src/services/vector/embedding_service.py
  - Log embedding dimension
  - Log model name
  - Log generation duration

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - test cases now include relevant historical context

---

## Phase 5: User Story 3 - Webhook Security and Request Validation (Priority: P3)

**Goal**: Harden production security by implementing comprehensive webhook validation and duplicate detection

**Independent Test**: Send webhook requests with valid and invalid signatures, verify only authenticated requests are processed and duplicates are rejected

### Tests for User Story 3 (Write FIRST, ensure they FAIL) ⚠️

- [ ] T056 [P] [US3] Unit test for idempotency cache in backend/tests/unit/services/test_idempotency_service.py
- [ ] T057 [P] [US3] Unit test for signature validation edge cases in backend/tests/unit/services/test_webhook_validation.py
- [ ] T058 [US3] Integration test for duplicate webhook handling in backend/tests/integration/test_idempotency.py
- [ ] T059 [US3] Integration test for signature validation failure in backend/tests/integration/test_webhook_security.py

### Data Models for User Story 3

- [ ] T060 [US3] Create IdempotencyCache model in backend/src/models/idempotency_cache.py
  - 1-hour TTL
  - Key: issue_number + event_type + delivery_id
  - Value: correlation_id

### Services for User Story 3

- [ ] T061 [US3] Implement IdempotencyService in backend/src/services/webhook/idempotency_service.py
  - Check Redis cache for duplicate (issue + event + delivery_id)
  - Store processed webhooks with 1-hour TTL (FR-017)
  - Return 409 Conflict if duplicate detected
- [ ] T062 [US3] Enhance WebhookService signature validation in backend/src/services/webhook/webhook_service.py
  - Validate HMAC-SHA256 signature (FR-012)
  - Handle missing signature (401 error)
  - Handle invalid signature (401 error)
  - Log validation attempts with correlation_id
- [ ] T063 [US3] Update WebhookService to integrate idempotency check in backend/src/services/webhook/webhook_service.py
  - Check IdempotencyService before processing
  - Store webhook in cache after validation
  - Return appropriate 409 response for duplicates

### Monitoring for User Story 3

- [ ] T064 [US3] Add structured logging for security events in backend/src/services/webhook/webhook_service.py
  - Log signature validation failures (per SC-008)
  - Log duplicate detection events
  - Log unauthorized access attempts
- [ ] T065 [US3] Add security metrics in backend/src/services/webhook/idempotency_service.py
  - Count duplicate detections
  - Count signature failures
  - Alert on anomalies
- [ ] T066 [US3] Create comprehensive README.md in backend/ with API documentation, architecture diagram, and service descriptions

**Checkpoint**: All user stories should now be independently functional - system is production-ready with security hardening

---

## Phase 6: Dashboard UI (Simple Monitoring)

**Goal**: Provide simple monitoring dashboard to display processing status, database contents, and test case statistics

**Independent Test**: Open dashboard, verify real-time stats display, issue list updates, and test case grid shows generated content

### Tests for Dashboard

- [ ] T067 [P] Unit test for DashboardStats endpoint in backend/tests/unit/api/test_dashboard.py
- [ ] T068 [P] Unit test for issues list endpoint in backend/tests/unit/api/test_issues_list.py
- [ ] T069 [P] Unit test for test cases list endpoint in backend/tests/unit/api/test_test_cases_list.py
- [ ] T070 [P] Component test for ProcessingStats in frontend/tests/components/ProcessingStats.test.tsx
- [ ] T071 [P] Component test for IssueList in frontend/tests/components/IssueList.test.tsx
- [ ] T072 [P] Component test for TestCaseGrid in frontend/tests/components/TestCaseGrid.test.tsx

### Backend API for Dashboard

- [ ] T073 [P] Create DashboardMetrics model in backend/src/models/dashboard_metrics.py
  - total_issues, pending, processing, completed, failed, skipped
  - avg_generation_time, total_prs_created, cache_hit_rate, vector_db_size
- [ ] T074 [P] Implement GET /api/stats endpoint in backend/src/api/dashboard.py
  - Aggregate statistics from ProcessingJob table
  - Return DashboardStats schema per openapi.yaml
- [ ] T075 [P] Implement GET /api/issues endpoint in backend/src/api/dashboard.py
  - Paginated list (limit, offset, status filter)
  - Return IssueStatus schema per openapi.yaml
- [ ] T076 [P] Implement GET /api/test-cases endpoint in backend/src/api/dashboard.py
  - Paginated list of TestCaseDocument
  - Return TestCase schema per openapi.yaml

### Frontend Components

- [ ] T077 [P] Create ProcessingStats component in frontend/src/components/ProcessingStats.tsx
  - Real-time metrics display (Recharts)
  - Auto-refresh every 5 seconds
  - Show pending, processing, completed, failed counts
  - Show avg generation time
- [ ] T078 [P] Create IssueList component in frontend/src/components/IssueList.tsx
  - Table with status badges
  - Pagination controls
  - GitHub issue links
  - Filter by status
- [ ] T079 [P] Create TestCaseGrid component in frontend/src/components/TestCaseGrid.tsx
  - Card layout
  - Markdown preview
  - PR links
  - Pagination
- [ ] T080 [P] Create DatabaseStatus component in frontend/src/components/DatabaseStatus.tsx
  - Vector DB size
  - Cache hit rate
  - Component health indicators (ChromaDB, Redis, Ollama)
- [ ] T081 Create Dashboard page in frontend/src/pages/Dashboard.tsx
  - Compose all components
  - Handle API errors
  - Show loading states
- [ ] T082 [P] Create API client service in frontend/src/services/api.ts
  - Axios instance with base URL
  - Type-safe API methods (getStats, getIssues, getTestCases, getHealth)
  - Error handling

### Frontend Setup

- [ ] T083 Setup TailwindCSS in frontend (simple styling per user requirement)
- [ ] T084 Configure React Router for dashboard navigation
- [ ] T085 Setup React Query for data fetching and caching
- [ ] T086 Create comprehensive README.md in frontend/ with component documentation, architecture, and usage examples

**Checkpoint**: Dashboard is functional and displays all monitoring data

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T087 [P] Add input validation for 5,000 character limit (FR-016) across all endpoints
- [ ] T088 [P] Add performance monitoring for <2min generation time (SC-001)
- [ ] T089 [P] Add concurrency testing for 100 concurrent requests (SC-002)
- [ ] T090 Implement daily TTL cleanup job for vector embeddings (30-day retention) using cron scheduler (2 AM UTC)
- [ ] T091 [P] Add Cloudflare Tunnel setup instructions to quickstart.md
- [ ] T092 [P] Validate quickstart.md setup guide with fresh environment
- [ ] T093 Run full integration test suite and verify 70%+ coverage
- [ ] T094 Run unit test suite and verify 80%+ coverage
- [ ] T095 [P] Security audit: verify no secrets in code, all env vars documented
- [ ] T096 [P] Performance testing: verify webhook <200ms p95 latency (plan.md constraint)
- [ ] T097 Add PR template in .github/PULL_REQUEST_TEMPLATE.md
- [ ] T098 Add issue templates in .github/ISSUE_TEMPLATE/ for bugs and features
- [ ] T099 Update .github/copilot-instructions.md with final implementation notes
- [ ] T100 Final code cleanup and refactoring pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - Core MVP, must complete first
- **User Story 2 (Phase 4)**: Depends on Foundational - Can start after or in parallel with US1 (different files)
- **User Story 3 (Phase 5)**: Depends on Foundational and US1 (enhances webhook service)
- **Dashboard (Phase 6)**: Depends on Foundational - Can start in parallel with US1/US2/US3 (frontend independent)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - **Critical Path**: T030-T034 (models) → T035 (webhook) → T036 (AI) → T037 (GitHub) → T039 (endpoint)
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 but independently testable
  - **Critical Path**: T049 (model) → T050 (embeddings) → T051 (vector service) → T052 (AI integration)
  - **Integration Point**: T052 updates T036 (AIService) - wait for T036 to complete
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances US1 webhook service
  - **Critical Path**: T060 (model) → T061 (idempotency) → T062 (signature) → T063 (integration)
  - **Integration Point**: T062-T063 update T035 (WebhookService) - wait for T035 to complete
- **Dashboard (Phase 6)**: Can start after Foundational (Phase 2) - Completely independent
  - **Critical Path**: T073 (model) → T074-T076 (API endpoints) || T077-T082 (frontend components in parallel)

### Within Each User Story

1. **Tests FIRST**: All test tasks (T022-T029, T045-T048, T056-T059, T067-T072) MUST be written and FAIL before implementation
2. **Models before services**: T030-T034 before T035-T038 (US1), T049 before T050-T053 (US2), T060 before T061-T063 (US3)
3. **Services before endpoints**: T035-T038 before T039 (US1)
4. **Core implementation before logging**: T035-T039 before T040-T042 (US1)
5. **Story complete before moving to next priority**: Checkpoint verification required

### Parallel Opportunities

**Phase 1 (Setup)**:

- T003, T004, T005 can run in parallel (different projects/languages)

**Phase 2 (Foundational)**:

- T010, T011, T012, T013, T018, T019, T020, T021 can all run in parallel (independent services)

**User Story 1 (Phase 3)**:

- Tests: T022-T029 can run in parallel (all write tests together)
- Models: T030-T034 can run in parallel (no dependencies between models)
- Logging: T040-T042 can run in parallel (add to respective services)

**User Story 2 (Phase 4)**:

- Tests: T045-T048 can run in parallel
- Services: T050 and T051 can run in parallel (embedding vs vector operations)
- Logging: T054 and T055 can run in parallel

**User Story 3 (Phase 5)**:

- Tests: T056-T059 can run in parallel

**Dashboard (Phase 6)**:

- Tests: T067-T072 can all run in parallel
- Backend API: T073-T076 can run in parallel (independent endpoints)
- Frontend: T077-T082 can all run in parallel (independent components)
- Setup: T083-T085 can run in parallel

**Across User Stories** (if team has capacity):

- US2 (Phase 4) and Dashboard (Phase 6) can both start after Foundational and proceed in parallel
- US3 (Phase 5) must wait for US1's WebhookService (T035) to be complete

**Phase 7 (Polish)**:

- T087-T099 (most tasks) can run in parallel except T093-T094 (run tests) and T100 (final cleanup)

---

## Parallel Example: User Story 1 Core Models

```bash
# After T029 (all US1 tests written and failing), these can execute in parallel:
git checkout -b feature/us1-models
# Terminal 1: Create WebhookEvent model
# Terminal 2: Create ProcessingJob model
# Terminal 3: Create TestCaseDocument model
# Terminal 4: Create GitHubPullRequest model
# Terminal 5: Create AgentState model

# All 5 models (T030-T034) complete in parallel, then merge and proceed to T035
```

---

## Parallel Example: Dashboard Components

```bash
# After T076 (all dashboard APIs complete), frontend can proceed entirely in parallel:
git checkout -b feature/dashboard-ui
# Terminal 1: ProcessingStats component (T077)
# Terminal 2: IssueList component (T078)
# Terminal 3: TestCaseGrid component (T079)
# Terminal 4: DatabaseStatus component (T080)
# Terminal 5: API client service (T082)

# All components ready in parallel, then compose into Dashboard page (T081)
```

---

## Implementation Strategy

### MVP Scope (Deliver First)

**Goal**: Minimum viable product for immediate value
**Timeline**: Focus on User Story 1 only
**Tasks**: Phase 1 → Phase 2 → Phase 3 (US1) → Minimal Dashboard (T070-T073 only)

**MVP Deliverables**:

- ✅ Webhook receives GitHub issues with "generate-tests" tag
- ✅ AI generates test cases using Llama 3.2 local server
- ✅ PR created automatically with test cases
- ✅ Basic API endpoints for monitoring (no UI yet)

**Success Criteria**: SC-001, SC-004, SC-005 verified

### Incremental Delivery

**Phase 3 Complete**: US1 MVP deployed, validated with real issues
**Phase 4 Add**: US2 context retrieval improves test quality (measure SC-007 improvement)
**Phase 5 Add**: US3 security hardening for production (SC-008 verification)
**Phase 6 Add**: Dashboard UI for monitoring (user-friendly interface)

### Validation Checkpoints

After each phase, verify:

- [ ] All tests passing (unit + integration)
- [ ] Coverage targets met (80% unit, 70% integration)
- [ ] Linting passes (ruff, ESLint)
- [ ] Quickstart guide works on fresh environment
- [ ] Performance targets met (SC-001, SC-002, SC-005)
- [ ] Security requirements met (SC-008)
- [ ] Constitution gates still passed (no complexity violations)

---

## Summary

**Total Tasks**: 100
**Task Breakdown by User Story**:

- Setup (Phase 1): 7 tasks
- Foundational (Phase 2): 14 tasks (BLOCKS all stories)
- User Story 1 - MVP (Phase 3): 21 tasks (9 tests + 12 implementation)
- User Story 2 - Context (Phase 4): 11 tasks (4 tests + 7 implementation)
- User Story 3 - Security (Phase 5): 10 tasks (4 tests + 6 implementation)
- Dashboard UI (Phase 6): 19 tasks (6 tests + 13 implementation)
- Polish (Phase 7): 18 tasks (cross-cutting)

**Parallel Opportunities**: 45 tasks marked with [P] can run in parallel within their phase

**Independent Test Criteria**:

- **US1**: Create tagged issue → verify PR created within 2 minutes
- **US2**: Create similar issues → verify context from previous issues used
- **US3**: Send invalid signature → verify 401 rejection + logging

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1) = **42 tasks** for core value delivery

**Estimated Effort**:

- MVP (42 tasks): ~2-3 weeks for 1 developer
- Full system (100 tasks): ~4-6 weeks for 1 developer
- With parallel execution (2-3 developers): ~2-3 weeks for full system

**Format Validation**: ✅ All tasks follow checklist format with [ID] [P?] [Story] Description + file paths
**Documentation Synchronization**: ✅ All README tasks inline with code implementation per Constitution IV
