# Data Models

This directory contains the core Pydantic data models for the test case generator backend.

## Overview

The models represent the domain entities and their lifecycle states in the AI-driven test case generation workflow. All models are **immutable** (frozen) and fully validated using Pydantic v2.

## Models

### 1. WebhookEvent

**Purpose**: Represents an incoming GitHub webhook event for issues with the `generate-tests` label.

**File**: `webhook_event.py`

**Key Attributes**:
- `event_id` (UUID): Unique identifier for idempotency tracking
- `event_type`: Either `"issues.opened"` or `"issues.labeled"`
- `issue_number`: GitHub issue number
- `issue_title`: Issue title (max 256 chars)
- `issue_body`: Issue description (truncated to 5000 chars)
- `labels`: List of labels (must contain `"generate-tests"`)
- `repository`: Full repo name (`owner/repo`)
- `signature`: HMAC-SHA256 webhook signature for verification
- `received_at`: Timestamp when webhook arrived
- `correlation_id` (UUID): For distributed tracing across services

**Validations**:
- Issue body auto-truncated to 5000 characters
- Labels list must contain at least one label
- Signature must match GitHub's HMAC format
- Repository must follow `owner/repo` format

**Immutability**: ✅ Frozen model

---

### 2. ProcessingJob

**Purpose**: Tracks the end-to-end status of a test case generation job through all workflow stages.

**File**: `processing_job.py`

**Key Attributes**:
- `job_id` (UUID): Unique job identifier
- `webhook_event_id` (UUID): Links to triggering WebhookEvent
- `status`: Current job state (see state machine below)
- `started_at`: Job creation timestamp
- `completed_at`: Job completion timestamp (nullable)
- `error_message`: Failure details (nullable)
- `error_code`: Error code from error-catalog.md (e.g., `"E301"`, `"E405"`)
- `retry_count`: Number of retry attempts (max 3)
- `retry_delays`: Exponential backoff delays `[5, 15, 45]` seconds
- `last_retry_at`: Most recent retry timestamp (nullable)
- `idempotency_key`: SHA256 hash (64 hex chars) for duplicate detection
- `current_stage`: Current workflow stage (see stages below)
- `correlation_id` (UUID): Shared tracking ID

#### State Machine

```
PENDING → PROCESSING → COMPLETED
                ↓
              FAILED
                ↓
             SKIPPED (after max retries or non-retryable error)
```

**JobStatus Enum**:
- `PENDING`: Job queued, not started
- `PROCESSING`: Active workflow execution
- `COMPLETED`: Successfully generated PR
- `FAILED`: Encountered error (may retry)
- `SKIPPED`: Permanently failed (no more retries)

#### Workflow Stages

**WorkflowStage Enum**:
1. `RECEIVE`: Webhook received and validated
2. `RETRIEVE`: Fetching context from vector DB
3. `GENERATE`: AI generating test cases (6 stages internally)
4. `COMMIT`: Committing files to Git branch
5. `CREATE_PR`: Creating GitHub pull request
6. `FINALIZE`: Adding comment and final updates

**Retry Logic**:
- **Retryable Errors** (E3xx, E4xx): Exponential backoff with 3 max retries
- **Non-Retryable Errors** (E1xx, E2xx, E5xx): Immediate SKIPPED status
- **Delays**: 5s → 15s → 45s between retries

**Immutability**: ✅ Frozen model

---

### 3. TestCaseDocument

**Purpose**: Represents a fully generated test case document ready for PR creation.

**File**: `test_case_document.py`

**Key Attributes**:
- `document_id` (UUID): Unique identifier
- `issue_number`: Source GitHub issue number
- `title`: Document title (e.g., `"Test Cases: Feature X"`)
- `content`: Full Markdown-formatted test case content
- `metadata`: Dict with required fields:
  - `issue`: Issue number
  - `generated_at`: Generation timestamp
  - `ai_model`: Model used (e.g., `"llama-3.2-11b"`)
  - `context_sources`: List of similar issue numbers
- `branch_name`: Git branch name (`test-cases/issue-{N}`)
- `pr_number`: GitHub PR number (nullable until created)
- `pr_url`: GitHub PR URL (nullable until created)
- `generated_at`: Generation timestamp
- `ai_model`: AI model identifier
- `context_sources`: List of similar issue IDs used for context
- `correlation_id` (UUID): Tracking ID

**Validations**:
- `content` must be valid Markdown (contains at least one heading `# Title`)
- `content` cannot be empty
- `metadata` must contain all 4 required fields
- `branch_name` format validated
- `pr_number` must be positive if set

**Immutability**: ✅ Frozen model

---

## Model Relationships

```
┌──────────────────┐
│  WebhookEvent    │
│  (event_id)      │
└────────┬─────────┘
         │ triggers
         ▼
┌──────────────────┐
│  ProcessingJob   │◄─── Tracks status through workflow
│  (job_id)        │
│  - webhook_event_id
│  - status         │
│  - current_stage  │
└────────┬─────────┘
         │ produces
         ▼
┌──────────────────┐
│ TestCaseDocument │
│ (document_id)    │
│  - issue_number  │
│  - pr_number     │
└──────────────────┘
```

**Key Relationships**:
1. **WebhookEvent → ProcessingJob**: One-to-one via `webhook_event_id`
2. **ProcessingJob → TestCaseDocument**: One-to-one via `issue_number` + `correlation_id`
3. **Correlation ID**: Shared UUID across all three models for distributed tracing

## Correlation ID Flow

All models share a `correlation_id` (UUID) generated at webhook ingestion:

```
Request → correlation_id=<uuid>
    ↓
WebhookEvent(correlation_id=<uuid>)
    ↓
ProcessingJob(correlation_id=<uuid>)
    ↓
TestCaseDocument(correlation_id=<uuid>)
    ↓
Logs, metrics, traces all tagged with correlation_id
```

This enables:
- End-to-end request tracing
- Log aggregation across services
- Performance monitoring per workflow
- Error debugging across stages

## Data Flow

1. **Webhook Ingestion**:
   - GitHub sends webhook → `WebhookEvent` created
   - Signature verified, payload validated
   - Idempotency key calculated (SHA256 hash)

2. **Job Creation**:
   - `ProcessingJob` created with status `PENDING`
   - Linked to `WebhookEvent` via `webhook_event_id`
   - Idempotency check (Redis cache, 1-hour TTL)

3. **Workflow Execution**:
   - Status: `PENDING` → `PROCESSING`
   - Stages: `RECEIVE` → `RETRIEVE` → `GENERATE` → `COMMIT` → `CREATE_PR` → `FINALIZE`
   - Each stage updates `current_stage` field

4. **Test Case Generation**:
   - `TestCaseDocument` created during `GENERATE` stage
   - Content validated (Markdown format)
   - Metadata populated with AI model + context sources

5. **PR Creation**:
   - Branch created: `test-cases/issue-{N}`
   - Files committed to branch
   - PR created → `pr_number` and `pr_url` populated
   - Status: `PROCESSING` → `COMPLETED`

6. **Error Handling**:
   - On failure: Status → `FAILED`, `error_code` set
   - Retry logic checks `error_code` (E3xx/E4xx = retryable)
   - After max retries: Status → `SKIPPED`

## Validation Rules

### WebhookEvent
- ✅ `event_type` must be `"issues.opened"` or `"issues.labeled"`
- ✅ `issue_body` auto-truncated to 5000 chars
- ✅ `labels` must contain at least one label
- ✅ `signature` format: `sha256=<hex>`

### ProcessingJob
- ✅ `retry_count` must be 0-3
- ✅ `idempotency_key` must be exactly 64 hex characters (SHA256)
- ✅ `status` transitions follow state machine
- ✅ `completed_at` only set when status is `COMPLETED` or `SKIPPED`

### TestCaseDocument
- ✅ `content` must contain at least one Markdown heading (`# Title`)
- ✅ `metadata` must have: `issue`, `generated_at`, `ai_model`, `context_sources`
- ✅ `branch_name` format: `test-cases/issue-{N}`
- ✅ `pr_number` only set after PR creation

## Usage Examples

### Creating a WebhookEvent
```python
from models.webhook_event import WebhookEvent
from datetime import datetime
import uuid

event = WebhookEvent(
    event_id=str(uuid.uuid4()),
    event_type="issues.labeled",
    issue_number=42,
    issue_title="Add user authentication",
    issue_body="We need OAuth2 support...",
    labels=["generate-tests", "enhancement"],
    repository="owner/repo",
    signature="sha256=abc123...",
    received_at=datetime.utcnow(),
    correlation_id=str(uuid.uuid4())
)
```

### Creating a ProcessingJob
```python
from models.processing_job import ProcessingJob, JobStatus, WorkflowStage
from datetime import datetime
import hashlib

job = ProcessingJob(
    job_id=str(uuid.uuid4()),
    webhook_event_id=event.event_id,
    status=JobStatus.PENDING,
    started_at=datetime.utcnow(),
    completed_at=None,
    error_message=None,
    error_code=None,
    retry_count=0,
    retry_delays=[5, 15, 45],
    last_retry_at=None,
    idempotency_key=hashlib.sha256(f"{event.repository}:{event.issue_number}".encode()).hexdigest(),
    current_stage=WorkflowStage.RECEIVE,
    correlation_id=event.correlation_id
)
```

### Creating a TestCaseDocument
```python
from models.test_case_document import TestCaseDocument

doc = TestCaseDocument(
    document_id=str(uuid.uuid4()),
    issue_number=42,
    title="Test Cases: User Authentication",
    content="# Test Cases\n\n## Scenario 1\n...",
    metadata={
        "issue": 42,
        "generated_at": datetime.utcnow().isoformat(),
        "ai_model": "llama-3.2-11b",
        "context_sources": [23, 35, 41]
    },
    branch_name="test-cases/issue-42",
    pr_number=None,
    pr_url=None,
    generated_at=datetime.utcnow(),
    ai_model="llama-3.2-11b",
    context_sources=[23, 35, 41],
    correlation_id=event.correlation_id
)
```

## Testing

All models have comprehensive unit tests in `tests/unit/models/`:
- `test_webhook_event.py`: 10+ test cases
- `test_processing_job.py`: 12+ test cases
- `test_test_case_document.py`: 8+ test cases

**Test Coverage**: 100% for model validation logic

## Error Handling

Models raise Pydantic `ValidationError` with detailed messages:
```python
try:
    event = WebhookEvent(...)
except ValidationError as e:
    # e.errors() contains field-level validation failures
    # e.json() returns JSON error details
    pass
```

Common validation errors:
- **E101**: Invalid event structure
- **E102**: Missing required fields
- **E103**: Invalid event type (not issues.opened/labeled)
- **E107**: Missing required label (`generate-tests`)

## Immutability Guarantees

All models use `model_config = ConfigDict(frozen=True)`:
```python
event = WebhookEvent(...)
event.issue_number = 99  # ❌ Raises ValidationError

# To "update", create a new instance:
updated_job = job.model_copy(update={"status": JobStatus.COMPLETED})
```

## See Also

- **Workflow Stages**: See `services/README.md` for full workflow details
- **Error Codes**: See `specs/001-ai-test-generation/error-catalog.md`
- **Test Template**: See `specs/001-ai-test-generation/test-case-template.md`
- **API Contracts**: See `specs/001-ai-test-generation/contracts/`
