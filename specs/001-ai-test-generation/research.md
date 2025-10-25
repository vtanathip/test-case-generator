# Technical Research: AI Test Case Generation System

**Date**: 2025-10-25  
**Purpose**: Document technology choices, architectural decisions, and best practices for the AI test case generation system.

## Research Areas

### 1. Vector Database Selection

**Decision**: Qdrant (primary choice) or ChromaDB (alternative)

**Rationale**:

- **Qdrant**: Production-ready, supports filtering, has Python client, Docker deployment, handles 30-day TTL via collection management
- **ChromaDB**: Simpler setup, embedded mode for development, good for smaller scale (~10k embeddings)
- Both support cosine similarity for test case retrieval (FR-004 requirement: top 5 results)
- Both integrate well with local embedding models (e.g., sentence-transformers, Llama 3.2 embeddings)

**Chosen**: ChromaDB for MVP simplicity, migrate to Qdrant if scale increases beyond 10k embeddings

**Embedding Strategy**:

- Use local embedding model (e.g., `all-MiniLM-L6-v2` from sentence-transformers) to eliminate external API dependency
- Alternative: Use Llama 3.2 itself for embeddings (experimental, may require custom implementation)
- Consistent with local-first architecture (no external AI APIs)

**Alternatives Considered**:

- Pinecone: Cloud-only, adds external dependency cost
- Weaviate: Over-engineered for simple similarity search use case
- PostgreSQL pgvector: Requires additional DB, adds complexity

**Best Practices**:

- Store embeddings with metadata (issue_id, created_at, similarity_threshold)
- Implement TTL cleanup job (runs daily to remove >30-day entries)
- Use batch insertion for performance
- Cache frequent queries (top patterns)

---

### 2. AI Workflow Orchestration (LangGraph)

**Decision**: LangGraph with Llama 3.2 on local server

**Rationale**:

- LangGraph provides state management for multi-step workflows (webhook → retrieve → generate → commit → PR)
- Supports conditional edges for retry logic (exponential backoff requirement)
- Built-in error handling and state persistence
- Python-native, integrates with FastAPI
- Llama 3.2 running locally eliminates API costs and rate limits
- Local inference provides consistent latency and data privacy
- No external API dependencies reduces operational complexity

**Workflow Stages**:

1. **Receive**: Parse webhook, validate signature
2. **Retrieve**: Query vector DB for context (max 5 results)
3. **Generate**: Call local Llama 3.2 with prompt template + context
4. **Commit**: Create branch, commit Markdown file
5. **Create PR**: Open PR, comment on issue

**Chosen Model**: Llama 3.2 (11B or 90B variant depending on hardware)

**Local Inference Stack**:

- **Ollama**: Simple local LLM server (recommended for ease of use)
- **vLLM**: High-performance inference server (if throughput critical)
- **llama.cpp**: Lightweight C++ implementation (if resource-constrained)

**Alternatives Considered**:

- OpenAI GPT-4: External API, costs per token, rate limits
- Anthropic Claude: External API, similar drawbacks as OpenAI
- Direct Transformers library: More complex setup than Ollama
- Custom state machine: Reinventing the wheel, violates YAGNI

**Best Practices**:

- Use streaming for long generations
- Implement timeout (120s per LLM call for local inference)
- Log all state transitions with correlation IDs
- Store agent state in Redis for crash recovery
- Monitor GPU memory usage and temperature
- Implement request queuing if GPU saturated

---

### 3. Idempotency Cache (Redis)

**Decision**: Redis with 1-hour TTL

**Rationale**:

- In-memory, sub-millisecond lookups (meets <10s webhook response requirement)
- Native TTL support (SET key value EX 3600)
- Simple key structure: `webhook:{issue_id}:{event_type}:{timestamp_bucket}`
- Lightweight, standard deployment

**Cache Key Design**:

```python
cache_key = f"webhook:{issue_number}:{event_type}:{timestamp // 300}"  # 5-min buckets
```

**Alternatives Considered**:

- In-memory dict: Lost on restart, no TTL management
- Database table: Too slow for <200ms p95 latency requirement
- Memcached: Less feature-rich than Redis, no persistence option

**Best Practices**:

- Use hash of payload for duplicate detection
- Log cache hits for monitoring
- Implement cache warming for startup
- Handle cache unavailability gracefully (log and proceed with warning)

---

### 4. Webhook Handling (FastAPI + Cloudflare Tunnel)

**Decision**: FastAPI with async handlers + Cloudflare Tunnel for public endpoint

**Rationale**:

- FastAPI: Async-native (handles 100 concurrent requests), automatic OpenAPI docs, simple deployment
- Cloudflare Tunnel: Secure public endpoint without exposing server IP, handles SSL, DDoS protection
- Background tasks: Use FastAPI BackgroundTasks for async processing (doesn't block webhook response)

**Webhook Flow**:

1. Receive POST /webhooks/github
2. Validate signature (HMAC SHA-256)
3. Check idempotency cache
4. Return 202 Accepted (within 10s)
5. Process in background: trigger LangGraph workflow

**Alternatives Considered**:

- ngrok: Less reliable for production, requires constant connection
- Reverse proxy: More complex setup, manual SSL management
- AWS Lambda: Adds cloud dependency, cold start latency

**Best Practices**:

- Use hmac.compare_digest for timing-safe signature verification
- Return 202 Accepted immediately, process async
- Log webhook payload for debugging (sanitize sensitive data)
- Implement rate limiting (100 req/s max)

---

### 5. GitHub Operations (PyGithub)

**Decision**: PyGithub library for GitHub API interactions

**Rationale**:

- Official GitHub Python SDK, well-maintained
- Supports all required operations: create branch, commit, PR, comments
- Handles authentication (token or GitHub App)
- Built-in retry logic for rate limits

**Operations Needed**:

- `repo.create_git_ref()`: Create branch test-cases/issue-{num}
- `repo.create_file()`: Commit test case Markdown
- `repo.create_pull()`: Open PR with issue link
- `issue.create_comment()`: Add PR link or failure message

**Alternatives Considered**:

- Direct REST API: More boilerplate, manual error handling
- GitHub CLI: Requires subprocess calls, harder to test
- Octokit.py: Less mature than PyGithub

**Best Practices**:

- Use GitHub App authentication (better rate limits than personal tokens)
- Implement exponential backoff for rate limit errors
- Cache repository object (avoid repeated API calls)
- Log all GitHub API calls with correlation IDs

---

### 6. Structured Logging (structlog)

**Decision**: structlog with JSON output format

**Rationale**:

- Native JSON logging (required per FR-013)
- Correlation ID support via context binding
- Integrates with FastAPI middleware
- Production-ready (used by major Python projects)

**Log Structure**:

```json
{
  "timestamp": "2025-10-25T10:30:45Z",
  "level": "info",
  "correlation_id": "uuid-1234",
  "event": "webhook_received",
  "issue_number": 42,
  "event_type": "issues.opened",
  "duration_ms": 150
}
```

**Alternatives Considered**:

- Standard logging: No structured output, harder to parse
- python-json-logger: Less feature-rich than structlog
- Loguru: No JSON support, prettier console output but not suitable for production

**Best Practices**:

- Bind correlation_id at webhook ingress
- Log at all workflow stages: webhook, cache check, vector query, LLM call, GitHub ops
- Use log levels correctly: INFO (normal flow), WARNING (retries), ERROR (failures)
- Aggregate logs to monitoring system (e.g., Grafana Loki)

---

### 7. Frontend Dashboard (React + TypeScript)

**Decision**: React with TypeScript + TailwindCSS + Recharts

**Rationale**:

- React: Component-based, easy to build simple dashboard
- TypeScript: Type safety for API contracts
- TailwindCSS: Rapid UI development, no custom CSS needed
- Recharts: Simple charting library for stats visualization

**Dashboard Components**:

1. **ProcessingStats**: Real-time metrics (issues processed, success rate, avg time)
2. **IssueList**: Table of recent issues with "generate-tests" tag, status (pending/processing/completed)
3. **TestCaseGrid**: Generated test cases with preview and GitHub PR links
4. **DatabaseStatus**: Vector DB size, cache hit rate, retention status

**API Endpoints**:

- `GET /api/stats`: Aggregated statistics
- `GET /api/issues?limit=50`: Recent issues with status
- `GET /api/test-cases?limit=50`: Generated test cases
- `GET /api/health`: System health (vector DB, cache, GitHub API)

**Alternatives Considered**:

- Vue.js: Less ecosystem support, smaller community
- Plain HTML/JS: Harder to maintain, no type safety
- Full-featured dashboard (Grafana): Over-engineered, requires separate setup

**Best Practices**:

- Use React Query for data fetching and caching
- Implement auto-refresh (every 5s) for real-time updates
- Show loading states and error messages
- Keep UI simple and focused (no fancy animations)

---

### 8. Testing Strategy

**Decision**: pytest with fixtures, httpx for API tests, pytest-asyncio for async code

**Test Levels**:

1. **Unit Tests** (80% coverage target):
   - Vector store operations (mock ChromaDB)
   - LangGraph workflow stages (mock LLM)
   - GitHub client (mock PyGithub)
   - Cache operations (mock Redis)

2. **Integration Tests** (70% coverage target):
   - Full webhook → PR flow (use test GitHub repo)
   - Vector DB queries with real embeddings
   - Redis cache behavior

3. **Contract Tests**:
   - GitHub API responses (use recorded responses)
   - OpenAI API format (use mock responses)

**Test Fixtures**:

- `mock_webhook_payload`: Sample GitHub webhook JSON
- `test_vector_db`: ChromaDB instance with test data
- `test_redis`: Redis instance cleared before each test
- `test_github_repo`: Fixture for GitHub API mocking

**Alternatives Considered**:

- unittest: Less Pythonic than pytest, more boilerplate
- pytest-bdd: Over-engineered for this use case
- No integration tests: Violates constitution testing requirements

**Best Practices**:

- Use AAA pattern (Arrange, Act, Assert)
- Mock external services (GitHub, OpenAI) in unit tests
- Use real services in integration tests (with test instances)
- Parametrize tests for edge cases
- Test error paths and retries explicitly

---

### 9. Deployment & Infrastructure

**Decision**: Docker Compose for MVP, Kubernetes for production

**MVP Stack**:

- Docker containers: backend, frontend, ChromaDB, Redis
- docker-compose.yml orchestrates all services
- Cloudflare Tunnel for webhook ingress
- GitHub Actions for CI/CD

**Container Architecture**:

```yaml
services:
  backend:
    image: python:3.11-slim
    ports: ["8000:8000"]
    environment: [GITHUB_TOKEN, OPENAI_API_KEY]
  
  frontend:
    image: node:20-alpine
    ports: ["3000:3000"]
  
  chromadb:
    image: chromadb/chroma:latest
    volumes: ["./data/chromadb:/chroma/data"]
  
  redis:
    image: redis:7-alpine
    command: ["redis-server", "--maxmemory", "256mb"]
```

**Alternatives Considered**:

- AWS Lambda + DynamoDB: Vendor lock-in, cold starts
- Kubernetes from start: Over-engineered for MVP
- Serverless framework: Adds abstraction layer

**Best Practices**:

- Use multi-stage Docker builds (smaller images)
- Mount volumes for persistent data (vector DB, Redis snapshots)
- Health check endpoints for all services
- Use environment variables for secrets (no hardcoding)
- Implement graceful shutdown (handle SIGTERM)

---

### 10. Test Case Template Format

**Decision**: Structured Markdown with YAML frontmatter

**Template Structure**:

```markdown
---
issue: #42
generated_at: 2025-10-25T10:30:00Z
ai_model: llama3.2:11b
context_sources: [issue-12, issue-38]
---

# Test Cases: [Issue Title]

## Test Scenario 1: [Scenario Name]

**Description**: [What is being tested]

**Given**: [Initial conditions]
**When**: [Action taken]
**Then**: [Expected outcome]

**Test Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Result**: [Detailed expected outcome]

**Edge Cases**:
- [Edge case 1]
- [Edge case 2]

---

## Test Scenario 2: [Another Scenario]
...
```

**Rationale**:

- YAML frontmatter: Machine-readable metadata for tracking
- Markdown body: Human-readable, GitHub-native rendering
- Given-When-Then: Standard BDD format, clear structure
- Edge cases inline: Keeps related information together

**Alternatives Considered**:

- JSON/YAML only: Not human-friendly in PR reviews
- Plain text: No structure, harder to parse
- Gherkin files: Over-formal, requires Cucumber-like tooling

**Best Practices**:

- Include correlation_id in frontmatter for debugging
- Link to source issue for traceability
- List AI model and context sources for transparency
- Keep scenarios concise (max 5 steps per test)

---

## Summary of Decisions

| Area | Technology | Rationale |
|------|------------|-----------|
| Vector DB | ChromaDB | Simple, embedded, sufficient for MVP scale |
| AI Workflow | LangGraph + Llama 3.2 (local) | State management, no API costs, data privacy |
| Embeddings | sentence-transformers (local) | No external API dependency, consistent with local-first |
| Cache | Redis | Fast, TTL support, standard deployment |
| Web Framework | FastAPI | Async, auto-docs, Python ecosystem |
| GitHub API | PyGithub | Official SDK, well-maintained |
| Logging | structlog | JSON output, correlation IDs |
| Frontend | React + TypeScript | Component-based, type-safe |
| Testing | pytest + httpx | Pythonic, async support |
| Deployment | Docker Compose | Simple orchestration for MVP |
| Test Format | Markdown + YAML | Human-readable, machine-parseable |
| LLM Inference | Ollama (recommended) | Simple setup, good performance |

---

## Next Steps

1. **Phase 1**: Generate data-model.md (entities and relationships)
2. **Phase 1**: Create API contracts (OpenAPI spec for backend endpoints)
3. **Phase 1**: Write quickstart.md (setup and run instructions)
4. **Phase 1**: Update agent context with selected technologies
