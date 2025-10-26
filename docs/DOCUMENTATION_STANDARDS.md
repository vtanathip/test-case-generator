# Documentation Standards

**Purpose**: Define documentation conventions for the test-case-generator project  
**Last Updated**: 2025-01-20  
**Based on**: specs/001-ai-test-generation/ specification documents

## Mandatory Documentation Sections

All technical documentation MUST include:

### 1. Header Metadata

```markdown
# Document Title

**Date**: YYYY-MM-DD  
**Branch**: 001-ai-test-generation  
**Status**: Draft | In Progress | Complete  
**Related**: [Links to related docs]
```

### 2. Prerequisites (Setup Docs)

- Software versions (Python 3.11+, Docker 24.0+, etc.)
- Hardware requirements (GPU, RAM, disk)
- Account requirements (GitHub, Cloudflare)
- Optional vs. required tools

**Example**:
```markdown
### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Docker | 24.0+ | Container orchestration |
```

### 3. Quick Start (User-Facing Docs)

- Numbered steps (1., 2., 3.)
- Bash commands with language tags (` ```bash`)
- Expected output or next steps
- Time estimates ("~5 minutes")

**Example**:
```markdown
### 1. Clone Repository

```bash
git clone https://github.com/owner/test-case-generator.git
cd test-case-generator
```

**Time**: ~1 minute
```

### 4. Architecture Overview (Technical Docs)

- Tech stack table (component, technology, purpose)
- ASCII diagrams for data flow
- Links to detailed implementation docs

**Example**:
```text
GitHub Webhook
     ↓
FastAPI Backend
     ↓
LangGraph Workflow → AI Service → GitHub PR
```

### 5. Error Handling (Code Docs)

- Error codes from error-catalog.md (E1xx-E5xx)
- Retry logic (exponential backoff delays)
- Non-retryable vs. retryable errors

**Example**:
```markdown
**Error Handling**:
- **E101**: Invalid webhook signature (non-retryable)
- **E301**: AI timeout (retryable: 5s, 15s, 45s delays)
```

## Markdown Conventions

### Headers

- `#` for document title (only one per file)
- `##` for major sections
- `###` for subsections
- `####` for sub-subsections (avoid deeper nesting)

### Code Blocks

Always use language tags:
```markdown
```bash
# Shell commands
docker-compose up -d
```

```python
# Python code
def example():
    pass
```

```text
# Plain text or ASCII art
Diagram here
```
```

### Links

Use relative paths for internal docs:
```markdown
See [LangGraph Implementation](./langgraph-implementation.md)
See [Specification](../specs/001-ai-test-generation/spec.md)
```

### Lists

**Unordered**:
```markdown
- Item 1
- Item 2
  - Sub-item (2 spaces indent)
```

**Ordered**:
```markdown
1. First step
2. Second step
3. Third step
```

**Task lists**:
```markdown
- [x] Completed task
- [ ] Pending task
```

### Emphasis

- **Bold** for critical information or labels
- *Italic* for emphasis
- `Code` for inline code, file names, commands
- **ALL CAPS** for sections requiring attention

**Example**:
```markdown
**Required**: Set `GITHUB_TOKEN` in `.env` file

*Note*: GPU is optional but recommended
```

### Tables

Use for structured data:
```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
```

### Emoji (Optional)

For visual hierarchy in user-facing docs:
- 🚀 Quick Start
- 📋 Prerequisites
- ⚡ Performance
- 🔒 Security
- 📊 Monitoring
- 🛠️ Configuration

**Use sparingly** - avoid in technical/API documentation.

## Required Documentation Files

### Project Root

- **README.md**: Project overview, quick start, architecture
  - Badges (tests, coverage, license)
  - Features list
  - Quick start (5 steps max)
  - Architecture diagram
  - Links to detailed docs
  - Tech stack table
  - Phase status

### docs/ Folder

- **DEVELOPER_GUIDE.md**: Complete setup, testing, development workflow
  - Prerequisites
  - Initial setup (clone, install, configure)
  - Running application (Docker + local)
  - Running tests (all commands)
  - Development workflow (TDD, git, code style)
  - Architecture overview
  - Troubleshooting

- **DOCUMENTATION_STANDARDS.md**: This file (conventions)

- **Technical Docs**: Implementation details
  - langgraph-implementation.md
  - uv-setup.md
  - (Others as needed)

### Code Documentation (backend/src/)

- **backend/src/models/README.md**: Data models
  - Overview section
  - Each model documented:
    - Purpose
    - Attributes (name, type, description)
    - Validation rules
    - State transitions (if applicable)
    - Relationships
    - Examples

- **backend/src/services/README.md**: Service architecture
  - Overview with diagram
  - Each service documented:
    - Purpose
    - Methods (signature, description, errors)
    - Dependencies
    - Error codes
    - Usage examples

- **backend/src/api/README.md**: API endpoints (if needed)
  - Endpoint list (method, path, description)
  - Request/response schemas
  - Error responses
  - Authentication

### Specification (specs/001-ai-test-generation/)

From `/speckit.plan` and `/speckit.tasks` commands:
- **spec.md**: Feature specification
- **plan.md**: Implementation plan
- **tasks.md**: Task breakdown
- **data-model.md**: Entity definitions
- **error-catalog.md**: Error codes
- **quickstart.md**: Quick start guide
- **research.md**: Research findings
- **contracts/**: API contracts

## Spec-Specific Standards

### Data Model Documentation

From `specs/001-ai-test-generation/data-model.md`:

**Required sections per entity**:
1. **Description**: One-line purpose
2. **Attributes**: Table with name, type, constraints, description
3. **Validation Rules**: List of validation logic
4. **Relationships**: How entity relates to others
5. **State Transitions**: State machine diagram (if applicable)
6. **Lifecycle**: Creation, updates, deletion rules

**Example**:
```markdown
### 1. WebhookEvent

**Description**: Represents an incoming GitHub webhook event.

**Attributes**:
- `event_id` (str, UUID): Unique identifier
- `event_type` (str): GitHub event type
- `issue_number` (int): GitHub issue number

**Validation Rules**:
- `event_type` must be "issues.opened" or "issues.labeled"
- `issue_body` truncated to 5000 chars

**Relationships**:
- One WebhookEvent → One ProcessingJob

**State**: Immutable once created
```

### Error Code Documentation

From `specs/001-ai-test-generation/error-catalog.md`:

**Format**:
```markdown
### E301: AI Service Timeout

**Category**: AI Generation  
**Severity**: ERROR  
**Retryable**: Yes (3 retries with exponential backoff)  
**Delays**: 5s, 15s, 45s

**Cause**: AI model generation exceeded timeout threshold

**User Impact**: PR creation delayed by retry delays

**Action**: Automatic retry, then comment on issue if all retries fail
```

### Performance Requirements

From `specs/001-ai-test-generation/plan.md`:

**Document constraints**:
- API response times (p95 latency)
- Resource limits (memory, CPU, disk)
- Throughput limits (requests/sec)
- Concurrency limits (max concurrent requests)
- Retention policies (data TTL)

**Example**:
```markdown
### Performance Requirements

- **Webhook Response**: <200ms p95 latency
- **End-to-End Generation**: <2min p95 from webhook to PR
- **Vector DB Query**: <500ms p95 for similarity search
- **Concurrent Requests**: 100 max without request dropping
```

## Cross-Reference Consistency

### Error Codes

All error codes MUST match `specs/001-ai-test-generation/error-catalog.md`:
- E1xx: Webhook validation errors
- E2xx: Vector database errors
- E3xx: AI generation errors
- E4xx: GitHub API errors
- E5xx: System errors

**Update all references** when error catalog changes.

### State Machines

Job status and workflow stages MUST match `specs/001-ai-test-generation/data-model.md`:

**JobStatus**:
- PENDING → PROCESSING → COMPLETED
- PROCESSING → FAILED
- PENDING → SKIPPED

**WorkflowStage**:
1. RECEIVE
2. RETRIEVE
3. GENERATE
4. COMMIT
5. CREATE_PR
6. FINALIZE

**Update all docs** when state machines change.

### Retry Logic

All retry documentation MUST match spec clarifications:
- **Retries**: Max 3 attempts
- **Delays**: 5s, 15s, 45s (exponential backoff)
- **Retryable**: E3xx, E4xx errors
- **Non-Retryable**: E1xx, E2xx, E5xx errors

### Performance Targets

Match `specs/001-ai-test-generation/spec.md` success criteria:
- Webhook response: <10s (FR-001)
- End-to-end: <2min p95 (SC-001)
- Vector DB query: <500ms p95 (FR-028)
- Concurrent requests: 100 (SC-002)
- Test coverage: 80% target
- Uptime: 99.9% (SC-005)

## Documentation Checklist

Before committing documentation changes:

- [ ] **Metadata**: Date, branch, status in header
- [ ] **Prerequisites**: Versions, tools, accounts listed
- [ ] **Code Blocks**: All have language tags (` ```bash`, ` ```python`)
- [ ] **Links**: Relative paths for internal docs
- [ ] **Error Codes**: Match error-catalog.md
- [ ] **State Machines**: Match data-model.md
- [ ] **Performance**: Match spec.md targets
- [ ] **Examples**: Tested and working
- [ ] **Spelling**: No typos (run spell check)
- [ ] **Consistency**: Terminology matches specs

## Validation Tools

Run before committing:

```bash
# Check markdown lint (if markdownlint installed)
markdownlint docs/**/*.md

# Check links (if markdown-link-check installed)
markdown-link-check docs/**/*.md

# Spell check (if aspell installed)
aspell check docs/DEVELOPER_GUIDE.md
```

## Common Terminology

Use consistent terms throughout documentation:

| Preferred | Avoid |
|-----------|-------|
| webhook event | webhook request |
| ProcessingJob | processing task, job record |
| correlation ID | request ID, trace ID |
| test case document | test case file, test doc |
| vector database | embedding database, vector DB |
| idempotency cache | duplicate cache, dedup cache |
| pull request | PR (spell out first use) |
| Llama 3.2 | LLaMA, llama (maintain capitalization) |

## Examples

### Good Documentation

✅ **Clear, structured, with examples**:
```markdown
### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

**Expected Output**:
```
90 passed, 1 skipped in 174.23s
```

**Coverage Target**: 80%
```

### Poor Documentation

❌ **Vague, no examples, no structure**:
```markdown
### Tests

Run tests with pytest. Use coverage if you want.
```

---

**Enforcement**: All PRs with documentation changes MUST follow these standards.

**Updates**: This document updated when spec standards change.

**Questions**: Contact maintainers or open GitHub issue.
