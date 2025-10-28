# Services

This directory contains the business logic services for the AI-driven test case generation workflow.

## Overview

The services implement a **6-stage workflow** orchestrated by LangGraph, processing GitHub webhook events through AI generation to pull request creation. All services include **structured logging** with correlation IDs for distributed tracing.

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Webhook                            │
│                  (issues.opened/labeled)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    WebhookService           │
        │  - Signature validation      │
        │  - Idempotency check         │
        │  - Label validation          │
        └─────────┬───────────────────┘
                  │ creates
                  ▼
        ┌─────────────────────────────┐
        │     ProcessingJob           │
        │   (status: PENDING)          │
        └─────────┬───────────────────┘
                  │
                  ▼
        ┌─────────────────────────────┐
        │       AIService             │
        │   (LangGraph Workflow)       │
        │                              │
        │  RECEIVE → RETRIEVE →        │
        │  GENERATE → COMMIT →         │
        │  CREATE_PR → FINALIZE        │
        └─────────┬───────────────────┘
                  │ uses
                  ▼
        ┌─────────────────────────────┐
        │    GitHubService            │
        │  - Branch creation           │
        │  - File commits              │
        │  - PR creation               │
        │  - Issue comments            │
        └─────────────────────────────┘
```

## Services

### 1. WebhookService

**Purpose**: Validates and processes incoming GitHub webhook events.

**File**: `webhook_service.py`

**Key Responsibilities**:
- **Signature Verification**: HMAC-SHA256 validation using GitHub webhook secret
- **Idempotency Check**: Redis-based duplicate detection (1-hour TTL)
- **Label Validation**: Ensures `generate-tests` label is present
- **Event Parsing**: Converts GitHub payload to `WebhookEvent` model

**Methods**:

#### `validate_signature(payload: bytes, signature: str) -> bool`
- Validates HMAC-SHA256 signature from GitHub
- Uses constant-time comparison to prevent timing attacks
- **Raises**: `InvalidWebhookSignatureError` (E101) if invalid

#### `check_idempotency(idempotency_key: str) -> bool`
- Checks Redis cache for duplicate webhook (1-hour TTL)
- Returns `True` if duplicate detected
- **Raises**: `DuplicateWebhookError` (E104) if duplicate

#### `validate_label(labels: List[str]) -> None`
- Ensures `generate-tests` label is present
- **Raises**: `InvalidWebhookPayloadError` (E107) if missing

#### `process_webhook(payload: bytes, signature: str, event_type: str) -> WebhookEvent`
- Main entry point for webhook processing
- Orchestrates validation steps
- Returns validated `WebhookEvent` model
- **Logs**: webhook_received, signature_validated, idempotency_checked, label_validated

**Dependencies**:
- `redis_client`: For idempotency tracking
- `config`: GitHub webhook secret

**Error Handling**:
- **E101**: Invalid webhook signature
- **E102**: Invalid payload structure
- **E103**: Invalid event type (not issues.opened/labeled)
- **E104**: Duplicate webhook (already processed)
- **E107**: Missing required label

---

### 2. AIService

**Purpose**: Orchestrates the 6-stage AI-powered test case generation workflow using LangGraph.

**File**: `ai_service.py`

**Key Responsibilities**:
- **State Management**: LangGraph state machine with `WorkflowState`
- **Context Retrieval**: Fetches similar test cases from vector DB
- **AI Generation**: Uses LLM to generate test cases in 6 sub-stages
- **Workflow Orchestration**: Routes through RECEIVE → RETRIEVE → GENERATE → COMMIT → CREATE_PR → FINALIZE
- **Error Recovery**: Handles timeouts, retries, and failures

#### LangGraph Workflow

The AIService implements a **directed graph** with 6 stages:

```
START
  │
  ▼
┌──────────┐
│ RECEIVE  │ Parse webhook, validate data
└────┬─────┘
     │
     ▼
┌──────────┐
│ RETRIEVE │ Query vector DB for similar test cases
└────┬─────┘
     │
     ▼
┌──────────┐
│ GENERATE │ AI generates test cases (6 sub-stages)
└────┬─────┘
     │
     ▼
┌──────────┐
│  COMMIT  │ Create branch, commit files
└────┬─────┘
     │
     ▼
┌──────────┐
│CREATE_PR │ Create pull request
└────┬─────┘
     │
     ▼
┌──────────┐
│ FINALIZE │ Add comment, update job status
└────┬─────┘
     │
     ▼
    END
```

#### WorkflowState

The state passed through all nodes:

```python
class WorkflowState(TypedDict):
    job: ProcessingJob              # Current job with status/stage
    webhook_event: WebhookEvent     # Original webhook data
    context: List[Dict]             # Similar test cases from vector DB
    test_document: TestCaseDocument # Generated test case document
    error: Optional[str]            # Error message if failed
    messages: List[BaseMessage]     # LangChain conversation history
```

#### Methods

##### `execute_workflow(webhook_event: WebhookEvent, job: ProcessingJob) -> ProcessingJob`
- Main entry point for workflow execution
- Initializes LangGraph state machine
- Invokes graph and tracks progress through stages
- Returns updated `ProcessingJob` with final status
- **Logs**: workflow_started, workflow_completed, workflow_failed (with duration)

##### `_receive_node(state: WorkflowState) -> WorkflowState`
- **Stage 1**: Validates webhook data, updates job status to `PROCESSING`
- **Logs**: receive_stage_started, receive_stage_completed

##### `_retrieve_node(state: WorkflowState) -> WorkflowState`
- **Stage 2**: Queries vector DB for similar test cases using embeddings
- Retrieves top-k similar issues for context
- **Logs**: retrieve_stage_started, retrieve_stage_completed (with result_count)
- **Raises**: `VectorDBQueryError` (E301) if query fails

##### `_generate_node(state: WorkflowState) -> WorkflowState`
- **Stage 3**: AI generates test cases using LLM
- **6 Sub-stages**:
  1. **Scenario Identification**: Extract test scenarios from issue
  2. **Edge Case Analysis**: Identify edge cases
  3. **Precondition Definition**: Define setup requirements
  4. **Expected Outcome Definition**: Define assertions
  5. **Test Case Formatting**: Format as Markdown
  6. **Review & Refinement**: Final validation
- **Timeout**: 300 seconds (5 minutes) per generation
- **Logs**: generation_started, generation_completed, generation_timeout, generation_failed (with model, duration, content_length)
- **Raises**: `AITimeoutError` (E302), `AIGenerationError` (E303)

##### `_commit_node(state: WorkflowState) -> WorkflowState`
- **Stage 4**: Creates branch and commits test case files
- Branch name: `test-cases/issue-{N}`
- **Logs**: commit_stage_started, commit_stage_completed

##### `_create_pr_node(state: WorkflowState) -> WorkflowState`
- **Stage 5**: Creates GitHub pull request
- PR title: `"Test Cases: {issue_title}"`
- Links to original issue in description
- **Logs**: create_pr_stage_started, create_pr_stage_completed (with pr_number)

##### `_finalize_node(state: WorkflowState) -> WorkflowState`
- **Stage 6**: Adds comment to issue with PR link, updates job status to `COMPLETED`
- **Logs**: finalize_stage_started, finalize_stage_completed

**Dependencies**:
- `llm_client`: LLM for AI generation (Llama 3.2 or OpenAI/Anthropic)
- `vector_db_client`: Qdrant/ChromaDB for context retrieval
- `github_service`: GitHub operations
- `embeddings`: Text embedding model

**Error Handling**:
- **E301**: Vector DB query failed
- **E302**: AI generation timeout (>300s)
- **E303**: AI generation failed
- **E401**: Branch creation failed
- **E403**: File commit failed
- **E404**: PR creation failed

---

### 3. GitHubService

**Purpose**: Handles all GitHub API operations (branches, commits, PRs, comments).

**File**: `github_service.py`

**Key Responsibilities**:
- **Branch Management**: Create branches with conflict detection
- **File Operations**: Commit files to repository
- **Pull Requests**: Create PRs with proper metadata
- **Comments**: Add status updates to issues
- **Rate Limiting**: Handles GitHub API rate limits with retries

**Methods**:

#### `create_branch(branch_name: str, base_branch: str = "main") -> None`
- Creates a new Git branch
- **Logs**: github_create_branch_started, github_create_branch_completed, github_create_branch_exists (warning), github_rate_limit_exceeded (error)
- **Raises**: 
  - `GitHubBranchExistsError` (E402) if branch exists
  - `GitHubRateLimitError` (E405) if rate limited
  - `GitHubAPIError` (E406) for other API errors

#### `commit_file(branch_name: str, file_path: str, content: str, commit_message: str) -> None`
- Commits a file to a branch
- **Raises**: `GitHubAPIError` (E403) if commit fails

#### `create_pr(title: str, body: str, head_branch: str, base_branch: str = "main") -> Dict[str, Any]`
- Creates a pull request
- Returns PR data with `number`, `html_url`, `state`
- **Logs**: github_create_pr_started, github_create_pr_completed (with pr_number, pr_url), github_create_pr_failed
- **Raises**: `GitHubAPIError` (E406) if PR creation fails

#### `create_pr_for_issue(issue_number: int, head_branch: str, test_document: TestCaseDocument) -> Dict[str, Any]`
- Creates PR specifically for a test generation job
- Auto-generates title: `"Test Cases: {issue_title}"`
- Links to original issue in body
- **Raises**: `GitHubAPIError` (E404) if PR creation fails

#### `add_comment(issue_number: int, comment: str) -> None`
- Adds a comment to an issue
- **Logs**: github_add_comment_started, github_add_comment_completed, github_add_comment_failed
- **Raises**: `GitHubAPIError` (E406) if comment fails

#### `create_branch_with_retry(branch_name: str, base_branch: str = "main", max_retries: int = 3) -> None`
- Creates branch with exponential backoff retries
- Retries on transient errors (network, rate limit)
- **Delays**: 5s → 15s → 45s
- **Raises**: `GitHubAPIError` (E406) after max retries

**Dependencies**:
- `github_client`: GitHub API client (PyGithub or custom wrapper)
- `config`: GitHub repository name and credentials

**Error Handling**:
- **E401**: Branch creation failed (conflict or invalid name)
- **E402**: Branch already exists
- **E403**: File commit failed
- **E404**: PR creation failed
- **E405**: GitHub rate limit exceeded
- **E406**: Generic GitHub API error

---

## Workflow Execution Flow

### 1. Webhook Ingestion
```
POST /webhooks/github
    ↓
WebhookService.process_webhook()
    ↓
Validate signature (HMAC-SHA256)
    ↓
Check idempotency (Redis cache)
    ↓
Validate label (generate-tests)
    ↓
Create WebhookEvent model
    ↓
Create ProcessingJob (status: PENDING)
```

### 2. Background Processing
```
Background Task (FastAPI BackgroundTasks)
    ↓
AIService.execute_workflow()
    ↓
LangGraph state machine invoked
```

### 3. LangGraph Workflow Stages

#### Stage 1: RECEIVE
```
_receive_node()
    ↓
Validate webhook_event
    ↓
Update job.status = PROCESSING
    ↓
Update job.current_stage = RECEIVE
```

#### Stage 2: RETRIEVE
```
_retrieve_node()
    ↓
Generate embedding for issue body
    ↓
Query vector DB (Qdrant/ChromaDB)
    ↓
Retrieve top-5 similar test cases
    ↓
Store in state.context
```

#### Stage 3: GENERATE (AI Generation - 6 Sub-stages)
```
_generate_node()
    ↓
Sub-stage 1: Scenario Identification
    ↓ (LLM prompt: "Identify test scenarios from issue")
Sub-stage 2: Edge Case Analysis
    ↓ (LLM prompt: "Identify edge cases")
Sub-stage 3: Precondition Definition
    ↓ (LLM prompt: "Define setup requirements")
Sub-stage 4: Expected Outcome Definition
    ↓ (LLM prompt: "Define assertions")
Sub-stage 5: Test Case Formatting
    ↓ (LLM prompt: "Format as Markdown")
Sub-stage 6: Review & Refinement
    ↓ (LLM prompt: "Validate and refine")
Create TestCaseDocument
    ↓
Store in state.test_document
```

#### Stage 4: COMMIT
```
_commit_node()
    ↓
GitHubService.create_branch("test-cases/issue-{N}")
    ↓
GitHubService.commit_file("tests/test_issue_{N}.md", content)
```

#### Stage 5: CREATE_PR
```
_create_pr_node()
    ↓
GitHubService.create_pr_for_issue(issue_number, head_branch, test_document)
    ↓
Store pr_number and pr_url in test_document
```

#### Stage 6: FINALIZE
```
_finalize_node()
    ↓
GitHubService.add_comment(issue_number, "✅ Test cases generated! PR: #{pr_number}")
    ↓
Update job.status = COMPLETED
    ↓
Update job.completed_at = now()
```

### 4. Error Handling
```
Any stage fails
    ↓
Catch exception
    ↓
Update job.status = FAILED
    ↓
Set job.error_code (E301, E302, etc.)
    ↓
Check if error is retryable
    ↓
If retryable: Schedule retry with backoff
    ↓
If not retryable: Set job.status = SKIPPED
```

## Correlation ID Tracking

All services use **correlation_id** (UUID) for distributed tracing:

```
Webhook arrives → correlation_id generated
    ↓
WebhookEvent(correlation_id=<uuid>)
    ↓
ProcessingJob(correlation_id=<uuid>)
    ↓
All log entries tagged with correlation_id
    ↓
TestCaseDocument(correlation_id=<uuid>)
```

**Benefits**:
- End-to-end request tracing across services
- Log aggregation by workflow instance
- Performance monitoring per job
- Error debugging with full context

## Structured Logging

All services use **structlog** for JSON-formatted logging in production.

**Log Format**:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "webhook_received",
  "correlation_id": "a1b2c3d4-...",
  "job_id": "e5f6g7h8-...",
  "operation": "process_webhook",
  "issue_number": 42,
  "repository": "owner/repo"
}
```

**Key Log Events**:
- **WebhookService**: webhook_received, signature_validated, idempotency_checked, duplicate_detected
- **AIService**: workflow_started, workflow_completed, generation_started, generation_completed (with duration_seconds)
- **GitHubService**: github_create_branch_started, github_create_pr_completed, github_rate_limit_exceeded

## Error Codes

Services raise exceptions with error codes from `error-catalog.md`:

### Webhook Validation (E1xx)
- **E101**: Invalid webhook signature
- **E102**: Invalid payload structure
- **E103**: Invalid event type
- **E104**: Duplicate webhook
- **E107**: Missing required label

### Vector DB (E3xx)
- **E301**: Vector DB query failed

### AI Generation (E3xx)
- **E302**: AI generation timeout (>300s)
- **E303**: AI generation failed

### GitHub Operations (E4xx)
- **E401**: Branch creation failed
- **E402**: Branch already exists
- **E403**: File commit failed
- **E404**: PR creation failed
- **E405**: GitHub rate limit exceeded
- **E406**: Generic GitHub API error

## Service Initialization

### FastAPI Lifespan Context

Services are initialized in `main.py` using FastAPI lifespan:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize clients
    redis_client = await init_redis(config)
    llm_client = await init_llm(config)
    vector_db_client = await init_vector_db(config)
    github_client = await init_github(config)
    
    # Initialize services
    webhook_service = WebhookService(redis_client, config)
    github_service = GitHubService(github_client, config)
    ai_service = AIService(llm_client, vector_db_client, github_service, config)
    
    # Store in app.state
    app.state.webhook_service = webhook_service
    app.state.ai_service = ai_service
    app.state.github_service = github_service
    
    yield
    
    # Cleanup
    await redis_client.close()
    await llm_client.close()
```

### Configuration

Services read from `src/core/config.py`:

```python
class Config:
    # GitHub
    github_webhook_secret: str
    github_token: str
    github_repo: str
    
    # AI
    llm_provider: str  # "llama" or "openai" or "anthropic"
    llm_model: str     # "llama-3.2-11b" or "gpt-4" or "claude-3"
    llm_timeout: int   # 300 seconds
    
    # Vector DB
    vector_db_provider: str  # "qdrant" or "chromadb"
    vector_db_url: str
    
    # Redis
    redis_url: str
    idempotency_ttl: int  # 3600 seconds (1 hour)
```

## Testing

All services have comprehensive unit tests in `tests/unit/services/`:

- **test_webhook_service.py**: 15+ test cases
  - Signature validation (valid/invalid/missing)
  - Idempotency checks (duplicate/unique)
  - Label validation (present/missing)
  - Payload parsing errors

- **test_ai_service.py**: 20+ test cases
  - Workflow execution (success/failure)
  - Each stage node (receive/retrieve/generate/commit/create_pr/finalize)
  - Error handling and retries
  - Timeout scenarios
  - State transitions

- **test_github_service.py**: 12+ test cases
  - Branch creation (success/exists/conflict)
  - File commits
  - PR creation (success/failure)
  - Comment addition
  - Rate limiting

**Test Coverage**: 54% overall (target: 80%)

### Integration Tests

Full workflow integration tests in `tests/integration/`:

- **test_webhook_to_pr_flow.py**: End-to-end webhook → PR flow
- **test_ai_workflow_stages.py**: LangGraph stage transitions
- **test_idempotency.py**: Duplicate webhook handling

**Integration Test Status**: 6/7 passing (1 skipped - retry logic FR-011)

## Performance Considerations

### LangGraph Workflow
- **Parallel Execution**: Stages run sequentially (no parallelism due to dependencies)
- **Timeout**: 300s per AI generation stage
- **Total Workflow Time**: ~30-60 seconds (RECEIVE: 1s, RETRIEVE: 5s, GENERATE: 20-40s, COMMIT: 5s, CREATE_PR: 5s, FINALIZE: 2s)

### Vector DB Queries
- **Top-K**: 5 similar test cases retrieved
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Query Time**: <5 seconds

### GitHub API
- **Rate Limits**: 5,000 requests/hour (authenticated)
- **Retry Logic**: 3 retries with exponential backoff (5s, 15s, 45s)
- **Timeout**: 10 seconds per request

## See Also

- **Models**: See `models/README.md` for data model details
- **Error Catalog**: See `specs/001-ai-test-generation/error-catalog.md`
- **LangGraph Implementation**: See `docs/langgraph-implementation.md`
- **Prompt Templates**: See `services/ai_prompt_template.py`
- **Test Case Template**: See `specs/001-ai-test-generation/test-case-template.md`
