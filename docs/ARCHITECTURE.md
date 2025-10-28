# System Architecture

This document provides a comprehensive overview of the AI Test Case Generator system architecture, including component interactions, data flow, and technology stack.

## Table of Contents

- [High-Level Overview](#high-level-overview)
- [System Components](#system-components)
- [Workflow Architecture](#workflow-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Network Architecture](#network-architecture)
- [Security Architecture](#security-architecture)
- [Scalability Considerations](#scalability-considerations)

---

## High-Level Overview

The AI Test Case Generator is a webhook-driven system that automatically generates comprehensive test case documentation from GitHub issues using local AI models.

### Architecture Diagram

```text
┌────────────────────────────────────────────────────────────────────┐
│                         GitHub Platform                            │
│                                                                     │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐          │
│  │  Issue   │────────▶│ Webhook  │────────▶│   API    │          │
│  │  Created │  Label  │  Trigger │  HTTP   │  Events  │          │
│  └──────────┘  Added  └──────────┘  POST   └────┬─────┘          │
│                                                   │                 │
└───────────────────────────────────────────────────┼─────────────────┘
                                                    │ HMAC Signed
                                                    │ JSON Payload
                                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                       Docker Environment                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                   FastAPI Backend                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │  │
│  │  │  Webhook API │→ │ Validation   │→ │ Job Queue    │     │  │
│  │  │  /webhooks/  │  │ + Signature  │  │ (Background) │     │  │
│  │  └──────────────┘  └──────────────┘  └──────┬───────┘     │  │
│  │                                               │              │  │
│  │                    ┌──────────────────────────▼──┐          │  │
│  │                    │   LangGraph Workflow       │          │  │
│  │                    │   (6-Stage State Machine)  │          │  │
│  │                    └──────────────┬──────────────┘          │  │
│  └───────────────────────────────────┼───────────────────────┘  │
│                                       │                           │
│  ┌───────────┬─────────────┬─────────┴────────┬──────────────┐  │
│  │           │             │                  │              │  │
│  ▼           ▼             ▼                  ▼              ▼  │
│  ┌─────┐  ┌─────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐   │
│  │Redis│  │Chroma│  │Embedding │  │  GitHub  │  │  Ollama │   │
│  │Cache│  │  DB  │  │ Service  │  │  Client  │  │(External│   │
│  └─────┘  └─────┘  └──────────┘  └──────────┘  └────┬────┘   │
│     ▲        ▲          ▲              │              │        │
│     │        │          │              │              │        │
│  Idempo-  Vector    384-dim         GitHub      host.docker   │
│  tency    Search    Embeddings       API      .internal:11434 │
│  Cache   Similar     (MiniLM)                                  │
│          Tests                                                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              React Dashboard (Frontend)                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │  Job     │  │  Logs    │  │  Metrics │             │   │
│  │  │  Status  │  │  Viewer  │  │  Charts  │             │   │
│  │  └──────────┘  └──────────┘  └──────────┘             │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
                         │                    ▲
                         │ Creates            │ Retrieves
                         ▼                    │
                   ┌──────────┐         ┌─────────┐
                   │  Branch  │         │   PR    │
                   │  Commit  │────────▶│ Created │
                   │  File    │         └─────────┘
                   └──────────┘
```

---

## System Components

### 1. GitHub Integration Layer

**Purpose:** Receives and validates webhook events from GitHub

**Components:**
- **Webhook Endpoint** (`/api/webhooks/github`)
  - HMAC-SHA256 signature verification
  - Event type filtering (issues.opened, issues.labeled)
  - Idempotency check using Redis cache
  - 202 Accepted response (<200ms)

**Technologies:**
- FastAPI for webhook handling
- Pydantic for request validation
- PyGithub for GitHub API operations

### 2. Processing Core (LangGraph Workflow)

**Purpose:** Orchestrates the 6-stage test case generation process

**State Machine Stages:**

```text
RECEIVE → RETRIEVE → GENERATE → COMMIT → CREATE_PR → FINALIZE
   ↓         ↓          ↓          ↓          ↓          ↓
Validate  Query DB  AI Generate  Git Push  Open PR   Comment
Event     Context   Test Cases   File      Request    on Issue
```

**Stage Details:**

1. **RECEIVE** (0.1-0.5s)
   - Validate webhook event
   - Extract issue metadata
   - Initialize job state
   - Check duplicate prevention

2. **RETRIEVE** (0.5-2s)
   - Convert issue body to 384-dim embedding
   - Query ChromaDB for similar test cases
   - Return top 5 most relevant context documents
   - Pass context to generation stage

3. **GENERATE** (20-45s)
   - Render Jinja2 prompt template with issue + context
   - Call Ollama API with Llama 3.2 model
   - Stream tokens from local AI model
   - Parse and validate generated test cases
   - Store result in state

4. **COMMIT** (2-5s)
   - Get repository default branch SHA
   - Create new branch: `test-cases/issue-N`
   - Create/update file: `test-cases/issue-N.md`
   - Commit test case content to branch

5. **CREATE_PR** (2-5s)
   - Generate PR title and body
   - Create pull request from test branch to main
   - Extract PR number and URL
   - Update job state with PR info

6. **FINALIZE** (1-3s)
   - Add comment to original issue
   - Include PR link in comment
   - Mark job as COMPLETED
   - Clean up resources

**Technologies:**
- LangGraph for state machine orchestration
- Python asyncio for concurrent operations
- Structured logging with correlation IDs

### 3. AI/ML Layer

**Purpose:** Generate test case content and perform semantic search

**Components:**

a) **Embedding Service**
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Converts text to vector embeddings
- Used for semantic similarity search
- Loaded on application startup

b) **LLM Client (Ollama)**
- Model: Llama 3.2 (2GB, 3B parameters) or Llama 3.2 11B
- Runs locally via Ollama server
- Accessed via HTTP API at `host.docker.internal:11434`
- Streaming response support
- 120-second timeout

**Model Selection:**
```text
┌────────────────┬──────────┬──────────┬────────────┐
│     Model      │   Size   │   Time   │  Quality   │
├────────────────┼──────────┼──────────┼────────────┤
│ llama3.2:3b    │   1.3GB  │  15-25s  │    Good    │
│ llama3.2:latest│   2GB    │  25-45s  │ Excellent  │
└────────────────┴──────────┴──────────┴────────────┘
```

**Prompt Engineering:**
- Structured Jinja2 templates
- Context injection from vector DB
- Few-shot learning from similar test cases
- Format enforcement for consistency

### 4. Data Storage Layer

**Purpose:** Cache, context storage, and idempotency

**Components:**

a) **Redis Cache**
- Idempotency keys (1-hour TTL)
- Job state caching
- Rate limiting counters
- Webhook deduplication
- Port: 6379

b) **ChromaDB (Vector Database)**
- Collection: `test_cases`
- Stores test case embeddings
- Semantic similarity search
- Automatic indexing
- Port: 8000

**Data Flow:**
```text
Issue Created → Embedding Generated → Stored in ChromaDB
                                            ↓
New Issue → Query Embedding → Search ChromaDB → Return Similar Tests
```

### 5. Frontend Dashboard

**Purpose:** Visualize job status and system metrics

**Components:**
- Job status tracking (PENDING, PROCESSING, COMPLETED, FAILED)
- Real-time log viewer
- Performance metrics charts
- Error rate monitoring
- Recent activity feed

**Technologies:**
- React 18 with TypeScript
- Vite for build and dev server
- TailwindCSS for styling
- React Router for navigation

---

## Workflow Architecture

### Complete Request Flow

```text
1. User creates GitHub issue with "generate-tests" label
   │
   ├─▶ GitHub triggers webhook event
   │
2. Webhook received by FastAPI endpoint
   │
   ├─▶ Verify HMAC signature
   ├─▶ Check idempotency cache (Redis)
   ├─▶ Return 202 Accepted
   │
3. Background task starts LangGraph workflow
   │
   ├─▶ RECEIVE: Parse event, create job
   │
   ├─▶ RETRIEVE: Generate embedding → Query ChromaDB
   │   └─▶ Find 0-5 similar test cases for context
   │
   ├─▶ GENERATE: Render prompt → Call Ollama → Stream response
   │   └─▶ Takes 20-45 seconds (AI generation)
   │
   ├─▶ COMMIT: Create branch → Commit file to GitHub
   │   └─▶ Branch: test-cases/issue-N
   │   └─▶ File: test-cases/issue-N.md
   │
   ├─▶ CREATE_PR: Open pull request (test branch → main)
   │   └─▶ Store PR number and URL
   │
   └─▶ FINALIZE: Add comment to issue with PR link
       └─▶ Mark job as COMPLETED
```

### Error Handling Flow

```text
Error Occurs at Any Stage
   │
   ├─▶ Catch exception in LangGraph node
   │
   ├─▶ Log error with correlation ID
   │
   ├─▶ Update job status to FAILED
   │
   ├─▶ Store error message and code
   │
   └─▶ Optional: Retry with exponential backoff
       (For transient failures: network, rate limits)
```

---

## Data Flow

### Webhook Event Processing

```text
GitHub Issue
   │ issue.opened OR issue.labeled
   │
   ▼
Webhook Event (JSON)
   │ event_type: "issues"
   │ action: "opened" | "labeled"
   │ issue: {...}
   │ repository: {...}
   │
   ▼
HMAC Verification
   │ signature = sha256(secret + body)
   │ compare with X-Hub-Signature-256 header
   │
   ▼ [Valid]
Idempotency Check (Redis)
   │ key = sha256(delivery_id + event_id)
   │ if exists → 409 Conflict
   │ else → store with 1h TTL
   │
   ▼ [New Event]
Background Task Queue
   │ Create ProcessingJob
   │ status = PENDING
   │
   ▼
LangGraph Workflow Execution
```

### Test Case Generation Flow

```text
Issue Body Text
   │
   ▼
Embedding Service
   │ all-MiniLM-L6-v2 model
   │
   ▼
384-dim Vector [0.123, -0.456, ...]
   │
   ▼
ChromaDB Query
   │ SELECT TOP 5 WHERE similarity > threshold
   │
   ▼
Similar Test Cases Context [0-5 documents]
   │
   ▼
Jinja2 Template Rendering
   │ Issue: {title, body, number}
   │ Context: {similar_tests}
   │
   ▼
Prompt (~3000 tokens)
   │
   ▼
Ollama API Request
   │ POST /api/generate
   │ model: llama3.2:latest
   │ stream: true
   │
   ▼
Stream Response (~4000 tokens, 25-45s)
   │
   ▼
Test Case Document
   │ Format: Markdown
   │ Size: 3000-6000 bytes
   │
   ▼
Commit to GitHub → PR Created
```

---

## Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | FastAPI | Latest | High-performance async API |
| **Language** | Python | 3.11+ | Application logic |
| **AI Workflow** | LangGraph | Latest | State machine orchestration |
| **HTTP Client** | httpx | Latest | Async HTTP for Ollama |
| **GitHub API** | PyGithub | Latest | Repository operations |
| **Validation** | Pydantic | 2.x | Data models and validation |
| **Logging** | structlog | Latest | Structured JSON logging |

### AI/ML Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **LLM Server** | Ollama | Latest | Local model serving |
| **LLM Model** | Llama 3.2 | 3B/11B | Test case generation |
| **Embeddings** | sentence-transformers | Latest | Text to vector conversion |
| **Embedding Model** | all-MiniLM-L6-v2 | Latest | 384-dim embeddings |
| **Vector DB** | ChromaDB | 0.4.24 | Semantic similarity search |

### Data Layer

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Cache** | Redis | 7-alpine | Idempotency + job state |
| **Vector DB** | ChromaDB | 0.4.24 | Test case embeddings |
| **Storage** | In-memory | - | Temporary job storage |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 18.x | UI framework |
| **Language** | TypeScript | 5.x | Type-safe JavaScript |
| **Build Tool** | Vite | Latest | Fast dev server + bundler |
| **Styling** | TailwindCSS | 3.x | Utility-first CSS |
| **Router** | React Router | 6.x | Client-side routing |

### Infrastructure

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Container** | Docker | 24.0+ | Service isolation |
| **Orchestration** | Docker Compose | 2.20+ | Multi-container deployment |
| **Reverse Proxy** | (Optional) Nginx | Latest | Load balancing |

---

## Network Architecture

### Docker Network Configuration

```text
┌─────────────────────────────────────────────────────────┐
│              Docker Bridge Network                       │
│                                                           │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐│
│  │   Backend   │───▶│   ChromaDB  │    │    Redis     ││
│  │  :8000      │    │   :8000     │    │    :6379     ││
│  └──────┬──────┘    └─────────────┘    └──────────────┘│
│         │                                                │
│         │ host.docker.internal:11434                    │
│         │ (Reaches host machine)                        │
│         ▼                                                │
└─────────┼─────────────────────────────────────────────┘
          │
    ┌─────┴──────┐
    │    Host    │
    │  Machine   │
    │            │
    │  Ollama    │
    │  :11434    │
    └────────────┘
```

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| Backend | 8000 | 8000 | API endpoints + webhooks |
| Frontend | 5173 | 3000 | Dashboard UI |
| ChromaDB | 8000 | 8000 | Vector database API |
| Redis | 6379 | 6379 | Cache access |
| Ollama | 11434 | 11434 | LLM API (on host) |

### External Integrations

```text
Internet
   │
   ├─▶ GitHub API (api.github.com)
   │   - Webhook delivery
   │   - Repository operations
   │   - Authentication: Bearer token
   │
   └─▶ (Optional) Monitoring Services
       - Application metrics
       - Error tracking
```

---

## Security Architecture

### Authentication & Authorization

**GitHub Integration:**
- Personal Access Token (PAT) with `repo` scope
- Stored in environment variables (never in code)
- Used for all GitHub API operations
- Token rotation supported

**Webhook Security:**
- HMAC-SHA256 signature verification
- Shared secret between GitHub and backend
- Signature in `X-Hub-Signature-256` header
- Prevents unauthorized webhook delivery

### Data Security

**At Rest:**
- No persistent storage of sensitive data
- Test cases stored in GitHub (user's repository)
- Redis cache with TTL (automatic expiration)
- ChromaDB embeddings are non-sensitive

**In Transit:**
- HTTPS for GitHub API communication
- Docker internal network for service communication
- No external exposure of internal services

### Input Validation

```text
Webhook Event
   │
   ├─▶ Signature Verification (Cryptographic)
   ├─▶ Event Type Validation (Whitelist)
   ├─▶ Pydantic Model Validation (Type Safety)
   └─▶ Idempotency Check (Duplicate Prevention)
```

### Rate Limiting

- GitHub API: 5,000 requests/hour (user token)
- Webhook processing: Limited by worker capacity
- Ollama: No rate limit (local)
- ChromaDB: No rate limit (local)

---

## Scalability Considerations

### Current Limitations

| Resource | Limit | Bottleneck |
|----------|-------|------------|
| **AI Generation** | 1 concurrent | Ollama single-threaded |
| **Backend Workers** | Configurable | CPU/Memory bound |
| **Vector DB** | 10k+ documents | Memory (ChromaDB) |
| **Cache** | Redis capacity | Memory |

### Horizontal Scaling Strategy

**Current Architecture (Single Instance):**
```text
[Backend] → [Ollama] → [ChromaDB] → [Redis]
   └─▶ Sequential processing
```

**Future: Multi-Instance with Queue:**
```text
[Backend 1] ─┐
[Backend 2] ─┼─▶ [Message Queue] ─▶ [Worker Pool] ─▶ [Ollama]
[Backend 3] ─┘                          ↓
                                   [ChromaDB] → [Redis]
```

### Performance Optimization

**Current Performance:**
- Webhook response: <200ms
- Total workflow: 30-60 seconds
- AI generation: 25-45 seconds (80% of total)

**Optimization Strategies:**
1. **Use smaller model** (llama3.2:3b) → 15-25s generation
2. **GPU acceleration** → 2-5x faster generation
3. **Batch processing** → Multiple issues in parallel
4. **Cache frequent patterns** → Reduce vector queries
5. **Background workers** → Scale webhook processing

### Resource Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 10GB
- Network: 10 Mbps

**Recommended:**
- CPU: 8+ cores (or GPU)
- RAM: 16GB
- Storage: 50GB
- Network: 100 Mbps

---

## Monitoring & Observability

### Logging Architecture

```text
Application Code
   │
   ├─▶ structlog (Structured Logging)
   │
   ├─▶ JSON Format
   │   {
   │     "event": "workflow_completed",
   │     "correlation_id": "abc123",
   │     "duration_seconds": 42.3,
   │     "level": "info"
   │   }
   │
   ├─▶ Docker Stdout/Stderr
   │
   └─▶ (Optional) Log Aggregation
       - ELK Stack
       - CloudWatch
       - Datadog
```

### Key Metrics

**Performance Metrics:**
- Webhook processing time (p50, p95, p99)
- AI generation time per request
- Vector DB query latency
- GitHub API call duration

**Business Metrics:**
- Total test cases generated
- Success/failure rate
- Average test case size
- Context relevance score

**Resource Metrics:**
- CPU usage per service
- Memory consumption
- Disk I/O
- Network throughput

### Health Checks

```text
GET /api/health
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "redis": "connected",
    "chromadb": "connected",
    "ollama": "connected",
    "github": "authenticated"
  }
}
```

---

## Deployment Architecture

### Docker Compose Stack

```yaml
services:
  backend:      # Python FastAPI application
  frontend:     # React dashboard
  chromadb:     # Vector database
  redis:        # Cache layer
  
# Note: Ollama runs on host, not in Docker
```

### Deployment Process

1. **Build Images:**
   ```bash
   docker-compose build
   ```

2. **Start Services:**
   ```bash
   docker-compose up -d
   ```

3. **Verify Health:**
   ```bash
   curl http://localhost:8000/api/health
   ```

4. **Configure Webhook:**
   - GitHub Settings → Webhooks
   - URL: `https://your-domain/api/webhooks/github`
   - Secret: Match `.env` value

### Environment Configuration

All environment-specific settings in `.env`:
- API keys and tokens
- Service endpoints
- Feature flags
- Resource limits

See [Configuration Documentation](../README.md#configuration) for details.

---

## Future Architecture Enhancements

### Planned Improvements

1. **Message Queue Integration**
   - RabbitMQ or Redis Queue
   - Decouple webhook receipt from processing
   - Better horizontal scaling

2. **Database Persistence**
   - PostgreSQL for job history
   - Metrics and analytics storage
   - Audit trail

3. **API Gateway**
   - Rate limiting
   - Authentication
   - Request routing

4. **Microservices Split**
   - Separate AI service
   - Independent scaling
   - Language flexibility

5. **Caching Layer**
   - Prompt response cache
   - Frequently generated patterns
   - Reduce AI calls

---

## Related Documents

- **Implementation Details:** [langgraph-implementation.md](./langgraph-implementation.md)
- **API Specification:** [openapi.yaml](../specs/001-ai-test-generation/contracts/openapi.yaml)
- **Developer Guide:** [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

**Last Updated:** 2025-10-28  
**Version:** 1.0.0  
**Architecture Version:** 1.0 (Single-instance Docker Compose)
