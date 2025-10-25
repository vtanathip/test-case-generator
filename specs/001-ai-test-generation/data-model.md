# Data Model: AI Test Case Generation System

**Date**: 2025-10-25  
**Purpose**: Define entities, relationships, state transitions, and validation rules for the system.

## Core Entities

### 1. WebhookEvent

**Description**: Represents an incoming GitHub webhook event.

**Attributes**:

- `event_id` (str, UUID): Unique identifier for this webhook event
- `event_type` (str): GitHub event type (e.g., "issues.opened", "issues.labeled")
- `issue_number` (int): GitHub issue number
- `issue_title` (str, max 256 chars): Issue title
- `issue_body` (str, max 5000 chars): Issue description (truncated if longer)
- `labels` (list[str]): Issue labels (e.g., ["generate-tests", "bug"])
- `repository` (str): Full repository name (e.g., "owner/repo")
- `signature` (str): GitHub webhook signature (HMAC-SHA256)
- `received_at` (datetime): Timestamp when webhook was received
- `correlation_id` (str, UUID): Correlation ID for tracing

**Validation Rules**:

- `event_type` must be "issues.opened" or "issues.labeled"
- `labels` must contain "generate-tests" tag
- `issue_body` truncated to 5000 chars with warning if longer
- `signature` must be valid HMAC-SHA256 of payload

**Relationships**:

- One WebhookEvent → One ProcessingJob
- One WebhookEvent → Zero or One TestCaseDocument (if successful)

**State**: Immutable once created

---

### 2. ProcessingJob

**Description**: Tracks the status of a test case generation workflow.

**Attributes**:

- `job_id` (str, UUID): Unique job identifier
- `webhook_event_id` (str, UUID): Reference to triggering webhook
- `status` (enum): Current job status
- `started_at` (datetime): Job start timestamp
- `completed_at` (datetime | null): Job completion timestamp
- `error_message` (str | null): Error details if failed
- `retry_count` (int, default 0): Number of retry attempts
- `current_stage` (str): Current workflow stage
- `correlation_id` (str, UUID): Shared with webhook event

**Status Enum**:

- `PENDING`: Job queued, not started
- `PROCESSING`: Currently executing
- `COMPLETED`: Successfully finished
- `FAILED`: Failed after all retries
- `SKIPPED`: Skipped (e.g., duplicate, invalid)

**Stage Values**:

- `RECEIVE`: Webhook received and validated
- `RETRIEVE`: Querying vector database for context
- `GENERATE`: AI generating test cases
- `COMMIT`: Creating branch and committing files
- `CREATE_PR`: Opening pull request
- `FINALIZE`: Adding comments and cleanup

**Validation Rules**:

- `retry_count` max 3 (per exponential backoff strategy)
- `completed_at` must be after `started_at`
- `error_message` required if status is FAILED
- `status` transitions must follow valid state machine

**Relationships**:

- One ProcessingJob → One WebhookEvent (many-to-one)
- One ProcessingJob → Zero or One TestCaseDocument (one-to-one)
- One ProcessingJob → Many AgentStateSnapshots (one-to-many)

**State Transitions**:

```text
PENDING → PROCESSING → COMPLETED
           ↓           ↑
           ↓      (retry if < 3)
           ↓           ↓
           └─────→ FAILED

PENDING → SKIPPED (if duplicate/invalid)
```

---

### 3. VectorEmbedding

**Description**: Stores embeddings of historical test cases for context retrieval.

**Attributes**:

- `embedding_id` (str, UUID): Unique embedding identifier
- `issue_number` (int): Source GitHub issue number
- `test_case_id` (str, UUID): Reference to TestCaseDocument
- `content` (str): Text content that was embedded
- `embedding_vector` (list[float], dim 1536): OpenAI embedding vector
- `metadata` (dict): Additional metadata (labels, repository, etc.)
- `created_at` (datetime): Creation timestamp
- `expires_at` (datetime): Expiration timestamp (created_at + 30 days)

**Validation Rules**:

- `embedding_vector` must have dimension 384 (all-MiniLM-L6-v2 format) or 768 (larger models)
- `expires_at` must be exactly 30 days after `created_at`
- `content` max 8000 chars (typical embedding model limit)

**Relationships**:

- Many VectorEmbeddings → One TestCaseDocument (many-to-one)
- VectorEmbeddings queried by similarity (cosine distance)

**Lifecycle**:

- Created: When test case PR is created
- Queried: During context retrieval (top 5 by similarity)
- Deleted: Daily cleanup job removes entries where `expires_at` < now

---

### 4. TestCaseDocument

**Description**: Generated test case document in Markdown format.

**Attributes**:

- `document_id` (str, UUID): Unique document identifier
- `issue_number` (int): Source GitHub issue number
- `title` (str): Test case document title
- `content` (str): Full Markdown content
- `metadata` (dict): YAML frontmatter (model, context sources, etc.)
- `branch_name` (str): Git branch name (e.g., "test-cases/issue-42")
- `pr_number` (int | null): GitHub PR number (null until PR created)
- `pr_url` (str | null): GitHub PR URL
- `generated_at` (datetime): Generation timestamp
- `ai_model` (str): AI model used (e.g., "llama-3.2-11b", "llama-3.2-90b")
- `context_sources` (list[int]): Issue numbers used for context
- `correlation_id` (str, UUID): Shared correlation ID

**Validation Rules**:

- `content` must be valid Markdown
- `metadata` must include: issue, generated_at, ai_model, context_sources
- `branch_name` must match pattern "test-cases/issue-{issue_number}"
- `pr_url` must be valid GitHub URL if not null

**Relationships**:

- One TestCaseDocument → One ProcessingJob (one-to-one)
- One TestCaseDocument → Many VectorEmbeddings (one-to-many, split by section)
- One TestCaseDocument → One GitHubPullRequest (one-to-one)

**Lifecycle**:

1. Generated by AI agent
2. Committed to Git branch
3. PR created (pr_number, pr_url populated)
4. Embedded and stored in vector DB

---

### 5. GitHubPullRequest

**Description**: Represents a GitHub pull request containing test cases.

**Attributes**:

- `pr_id` (str): GitHub PR ID (from API)
- `pr_number` (int): PR number in repository
- `pr_url` (str): Full PR URL
- `issue_number` (int): Source issue number
- `branch_name` (str): Source branch
- `title` (str): PR title
- `body` (str): PR description (includes link to issue)
- `state` (enum): PR state (OPEN, MERGED, CLOSED)
- `created_at` (datetime): PR creation timestamp
- `merged_at` (datetime | null): PR merge timestamp

**State Enum**:

- `OPEN`: PR is open for review
- `MERGED`: PR has been merged
- `CLOSED`: PR closed without merging

**Validation Rules**:

- `pr_url` must match pattern `https://github.com/{owner}/{repo}/pull/{number}`
- `body` must include reference to source issue (e.g., "Closes #42")
- `merged_at` must be after `created_at` if not null

**Relationships**:

- One GitHubPullRequest → One TestCaseDocument (one-to-one)
- One GitHubPullRequest → One GitHub Issue (external, linked by issue_number)

**Lifecycle**:

1. Created after test case commit
2. Updated when state changes (webhook or polling)
3. Finalized when merged or closed

---

### 6. AgentState

**Description**: Tracks LangGraph agent workflow state.

**Attributes**:

- `state_id` (str, UUID): Unique state identifier
- `job_id` (str, UUID): Reference to ProcessingJob
- `current_stage` (str): Current stage name (matches ProcessingJob.current_stage)
- `stage_data` (dict): Stage-specific data (context, results, errors)
- `next_stage` (str | null): Next stage to execute
- `retry_after` (datetime | null): Scheduled retry time (for exponential backoff)
- `updated_at` (datetime): Last update timestamp

**Stage Data Examples**:

```python
# RETRIEVE stage
{
  "query": "issue content",
  "results": [{"issue": 12, "similarity": 0.85}, ...],
  "result_count": 5
}

# GENERATE stage
{
  "prompt": "...",
  "response": "...",
  "token_count": 2400,
  "duration_ms": 8500
}

# COMMIT stage
{
  "branch": "test-cases/issue-42",
  "commit_sha": "abc123...",
  "file_path": "test-cases/issue-42.md"
}
```

**Validation Rules**:

- `stage_data` must be JSON-serializable
- `retry_after` only set if stage failed and retry_count < 3
- `next_stage` must be valid stage name or null (end of workflow)

**Relationships**:

- Many AgentStateSnapshots → One ProcessingJob (many-to-one)

**Lifecycle**:

- Created at workflow start
- Updated at each stage transition
- Persisted to Redis for crash recovery
- Deleted after job completion (after 1 hour retention)

---

### 7. IdempotencyCache

**Description**: Stores processed webhook signatures to prevent duplicate processing.

**Attributes**:

- `cache_key` (str): Composite key (issue_number + event_type + timestamp_bucket)
- `webhook_signature` (str): HMAC signature of webhook payload
- `processed_at` (datetime): When webhook was processed
- `expires_at` (datetime): TTL expiration (processed_at + 1 hour)

**Key Format**:

```python
cache_key = f"webhook:{issue_number}:{event_type}:{timestamp // 300}"
# Example: "webhook:42:issues.opened:1729858800"
# 5-minute buckets (300 seconds) for grouping
```

**Validation Rules**:

- `cache_key` must be unique within TTL window
- `expires_at` must be exactly 1 hour after `processed_at`

**Relationships**:

- Standalone entity (no foreign keys, pure cache)

**Lifecycle**:

- Created: When webhook processed
- Checked: On every webhook received (before processing)
- Deleted: Automatic Redis TTL expiration after 1 hour

---

### 8. DashboardMetrics

**Description**: Aggregated metrics for dashboard display (computed, not stored).

**Attributes**:

- `total_issues_processed` (int): Count of all processed issues
- `success_rate` (float): Percentage of successful generations
- `average_processing_time` (float): Mean time from webhook to PR (seconds)
- `p95_processing_time` (float): 95th percentile processing time
- `concurrent_jobs` (int): Currently processing jobs
- `failed_jobs_today` (int): Failed jobs in last 24 hours
- `vector_db_size` (int): Number of embeddings in database
- `cache_hit_rate` (float): Percentage of cache hits vs total requests
- `last_updated` (datetime): Metrics calculation timestamp

**Validation Rules**:

- All rates/percentages between 0.0 and 1.0
- Time metrics in seconds (non-negative)

**Relationships**:

- Derived from ProcessingJob, VectorEmbedding, IdempotencyCache entities

**Computation**:

- Calculated on-demand via SQL/aggregation queries
- Cached for 5 seconds (dashboard refresh rate)
- No persistent storage

---

## Entity Relationships Diagram

```text
┌─────────────────┐
│ WebhookEvent    │
│ - event_id      │
│ - issue_number  │
│ - signature     │
└────────┬────────┘
         │ 1:1
         ↓
┌─────────────────┐
│ ProcessingJob   │
│ - job_id        │
│ - status        │
│ - current_stage │
└────────┬────────┘
         │ 1:1              1:many
         ↓                     ↓
┌─────────────────┐     ┌──────────────┐
│ TestCaseDocument│     │ AgentState   │
│ - document_id   │     │ - state_id   │
│ - pr_number     │     │ - stage_data │
└────────┬────────┘     └──────────────┘
         │ 1:1
         ↓
┌─────────────────┐
│ GitHubPullRequest│
│ - pr_number     │
│ - state         │
└─────────────────┘
         
TestCaseDocument ──1:many──> VectorEmbedding
                              - embedding_vector
                              - expires_at

IdempotencyCache (standalone, no relationships)
DashboardMetrics (computed, no persistence)
```

---

## State Machine: ProcessingJob

```text
Initial State: PENDING

PENDING:
  - on_start → PROCESSING (trigger: background task)
  - on_duplicate → SKIPPED (trigger: cache hit)

PROCESSING:
  - on_success → COMPLETED (all stages done)
  - on_error + retry_count < 3 → PROCESSING (after backoff delay)
  - on_error + retry_count >= 3 → FAILED

COMPLETED:
  - terminal state (no transitions)

FAILED:
  - terminal state (no transitions)

SKIPPED:
  - terminal state (no transitions)
```

---

## Validation Summary

| Entity | Key Constraints |
|--------|----------------|
| WebhookEvent | Signature valid, body ≤ 5000 chars, "generate-tests" label present |
| ProcessingJob | Max 3 retries, valid state transitions, correlation_id consistency |
| VectorEmbedding | 1536-dim vector, 30-day TTL, content ≤ 8000 chars |
| TestCaseDocument | Valid Markdown, metadata complete, branch name pattern match |
| GitHubPullRequest | Valid GitHub URL, issue reference in body |
| AgentState | JSON-serializable stage_data, valid stage transitions |
| IdempotencyCache | 1-hour TTL, unique keys within window |
| DashboardMetrics | Non-negative values, rates in [0, 1] range |

---

## Storage Implementation

| Entity | Storage Backend | Retention |
|--------|-----------------|-----------|
| WebhookEvent | Application logs (JSON) | 30 days |
| ProcessingJob | PostgreSQL (if added) or in-memory + logs | 90 days |
| VectorEmbedding | ChromaDB | 30 days (auto-cleanup) |
| TestCaseDocument | GitHub (Git) + metadata in logs | Permanent (Git history) |
| GitHubPullRequest | GitHub API (external) | N/A (GitHub managed) |
| AgentState | Redis | 1 hour after completion |
| IdempotencyCache | Redis | 1 hour (TTL) |
| DashboardMetrics | Computed on-demand | Not stored |

**Note**: For MVP, ProcessingJob and TestCaseDocument metadata can be stored in structured logs instead of a database, simplifying deployment per simplicity principle.

---

## Next Steps

1. Generate API contracts (OpenAPI spec) based on these entities
2. Create quickstart.md with setup instructions
3. Update agent context file with selected technologies
