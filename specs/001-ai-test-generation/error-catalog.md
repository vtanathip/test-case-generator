# Error Catalog: AI Test Case Generation System

**Purpose**: Standardized error codes, messages, and handling procedures  
**Version**: 1.0  
**Date**: 2025-10-26

---

## Error Code Structure

Format: `E{category}{number}`

**Categories**:
- **E1xx**: Webhook & Input Validation Errors
- **E2xx**: Vector Database Errors
- **E3xx**: AI Generation Errors
- **E4xx**: GitHub API Errors
- **E5xx**: System & Infrastructure Errors

---

## E1xx: Webhook & Input Validation Errors

### E101: Invalid Webhook Signature

**Severity**: HIGH (Security)  
**HTTP Status**: 401 Unauthorized

**Internal Message**: `Webhook signature validation failed: expected={expected_sig}, received={received_sig}`

**User-Facing Message**: `Authentication failed. Please verify your webhook secret is correctly configured.`

**Action**:
- Log full request details (sanitized)
- Increment security metric counter
- Return 401 immediately, do not process

**Recovery**: User must verify GitHub webhook secret matches server configuration

---

### E102: Missing Required Tag

**Severity**: LOW  
**HTTP Status**: 200 OK (Acknowledged but not processed)

**Internal Message**: `Issue #{issue_number} does not contain required tag 'generate-tests'`

**User-Facing Message**: None (silent skip)

**Action**:
- Log event
- Return 200 OK
- Do not create ProcessingJob

**Recovery**: User adds "generate-tests" tag to issue

---

### E103: Issue Body Exceeds Character Limit

**Severity**: MEDIUM  
**HTTP Status**: 200 OK (Processed with truncation)

**Internal Message**: `Issue #{issue_number} body exceeds 5000 chars (actual: {actual_chars}), truncating`

**User-Facing Message** (GitHub comment):
```
⚠️ **Notice**: Your issue description was truncated to 5,000 characters for processing. 
The test cases below are based on the truncated content. For complete coverage, 
consider breaking this into multiple smaller issues.

Original length: {actual_chars} characters  
Processed length: 5,000 characters
```

**Action**:
- Truncate to 5000 chars
- Post warning comment
- Continue processing
- Log truncation

**Recovery**: None needed, graceful degradation

---

### E104: Insufficient Information

**Severity**: MEDIUM  
**HTTP Status**: 200 OK

**Internal Message**: `Issue #{issue_number} lacks sufficient detail for test case generation`

**User-Facing Message** (GitHub comment):
```
👋 Hi @{author}!

I attempted to generate test cases for this issue, but I need more information. 
Could you please provide:

- Clear description of the feature or functionality
- Expected behavior and acceptance criteria
- Any specific edge cases or error scenarios to consider
- Example inputs and expected outputs (if applicable)

Once you add these details, re-trigger generation by adding a comment with `/generate-tests`.

**Tip**: The more specific you are, the better the test cases will be! 🎯
```

**Action**:
- Post comment requesting details
- Mark ProcessingJob as SKIPPED (reason: "insufficient_information")
- Do not create PR

**Recovery**: User updates issue, manually re-triggers

---

### E105: Malformed Webhook Payload

**Severity**: HIGH  
**HTTP Status**: 400 Bad Request

**Internal Message**: `Failed to parse webhook payload: {parse_error}`

**User-Facing Message**: `Invalid webhook payload format`

**Action**:
- Log full payload (sanitized)
- Return 400 Bad Request
- Alert if > 5 occurrences in 5 minutes (possible attack)

**Recovery**: GitHub should retry; check webhook configuration

---

### E106: Duplicate Webhook Event (Idempotency)

**Severity**: LOW  
**HTTP Status**: 200 OK

**Internal Message**: `Duplicate webhook event detected: issue={issue_number}, event={event_id}, original_job={job_id}`

**User-Facing Message**: None

**Action**:
- Check idempotency cache (Redis)
- Return 200 OK
- Log event
- Do not create new ProcessingJob

**Recovery**: None needed, expected behavior

---

## E2xx: Vector Database Errors

### E201: Vector DB Connection Failed

**Severity**: HIGH  
**HTTP Status**: 200 OK (Degraded mode)

**Internal Message**: `Failed to connect to ChromaDB at {db_url}: {error_message}`

**User-Facing Message** (GitHub comment):
```
⚠️ **Processing Notice**: Test cases generated without historical context due to 
temporary database unavailability. Quality may be reduced.

I'll still create test cases based on your issue description alone.
```

**Action**:
- Log error with correlation ID
- Continue processing WITHOUT context retrieval
- Post warning comment
- Alert operations team
- Increment degraded mode counter

**Recovery**: Auto-retry next request; ops team investigates

---

### E202: Vector DB Query Timeout

**Severity**: MEDIUM  
**HTTP Status**: 200 OK (Degraded mode)

**Internal Message**: `Vector DB query timeout after {timeout}ms for issue #{issue_number}`

**User-Facing Message**: Same as E201

**Action**:
- Log timeout
- Continue without context
- Post warning comment

**Recovery**: Auto-retry next request

---

### E203: No Similar Test Cases Found

**Severity**: LOW  
**HTTP Status**: 200 OK

**Internal Message**: `No similar test cases found for issue #{issue_number} (similarity threshold < 0.7)`

**User-Facing Message**: None (silent, expected for new domains)

**Action**:
- Log event
- Continue generation without context
- No user notification needed

**Recovery**: None needed

---

### E204: Vector DB Storage Failed

**Severity**: MEDIUM  
**HTTP Status**: 200 OK (PR still created)

**Internal Message**: `Failed to store generated test case embedding: {error}`

**User-Facing Message**: None

**Action**:
- Log error
- Continue with PR creation (primary function succeeds)
- Background retry job attempts storage again
- Alert if > 10% failure rate

**Recovery**: Background job retries; ops investigates if persistent

---

## E3xx: AI Generation Errors

### E301: AI Service Timeout

**Severity**: HIGH  
**HTTP Status**: 200 OK (Retry)

**Internal Message**: `AI generation timeout after {timeout}s for issue #{issue_number}, attempt {retry_count}/3`

**User-Facing Message** (after 3 retries, GitHub comment):
```
❌ **Test Case Generation Failed**

I tried to generate test cases for this issue 3 times, but the AI service timed out. 
This might be due to high load or a complex issue description.

**What you can do**:
1. Try again in a few minutes by commenting `/generate-tests`
2. Simplify your issue description to reduce processing time
3. Break complex features into smaller issues

If this persists, please contact support with issue #{issue_number}.
```

**Action**:
- Retry with exponential backoff: 5s, 15s, 45s
- After 3 retries, mark job as FAILED
- Post failure comment
- Alert operations team

**Recovery**: User manually retries; ops investigates

---

### E302: AI Service Unavailable

**Severity**: CRITICAL  
**HTTP Status**: 200 OK (Retry)

**Internal Message**: `AI service (Ollama) unavailable at {ollama_url}: {error}`

**User-Facing Message** (GitHub comment):
```
❌ **Service Temporarily Unavailable**

The test case generation service is currently unavailable. I'll automatically retry 
in a few minutes.

Status: Attempt {retry_count}/3
Next retry: {next_retry_time}

No action needed on your part. You'll be notified when test cases are ready! 🔄
```

**Action**:
- Retry with exponential backoff
- Post status comment after each retry
- After 3 retries, mark FAILED and alert
- Page on-call engineer

**Recovery**: Ops team restarts Ollama service

---

### E303: AI Generated Invalid Output

**Severity**: MEDIUM  
**HTTP Status**: 200 OK (Regenerate)

**Internal Message**: `AI output failed validation: {validation_errors} for issue #{issue_number}`

**User-Facing Message** (GitHub comment - if regeneration also fails):
```
⚠️ **Generation Quality Issue**

I generated test cases, but they didn't meet quality standards. I'll try again with 
different parameters.

Attempt {retry_count}/2

If this persists, the issue description might be ambiguous. Consider:
- Adding more specific acceptance criteria
- Including example inputs/outputs
- Clarifying expected behavior
```

**Action**:
- Parse validation errors (missing scenarios, invalid format, etc.)
- Retry generation with adjusted prompt
- Maximum 2 retries
- If still fails, create partial output with quality warning

**Recovery**: Auto-retry with prompt adjustment; user clarifies issue if needed

---

### E304: AI Context Window Exceeded

**Severity**: MEDIUM  
**HTTP Status**: 200 OK (Truncate and process)

**Internal Message**: `Combined prompt + context exceeds 8192 tokens (actual: {token_count}), reducing context`

**User-Facing Message**: None (transparent handling)

**Action**:
- Reduce number of similar test cases from 3 to 2
- If still exceeds, reduce to 1
- If still exceeds, truncate issue body further
- Log token management decision
- Continue processing

**Recovery**: None needed, automatic handling

---

## E4xx: GitHub API Errors

### E401: GitHub API Rate Limit Exceeded

**Severity**: HIGH  
**HTTP Status**: 200 OK (Delayed retry)

**Internal Message**: `GitHub API rate limit exceeded: reset_at={reset_time}, remaining=0`

**User-Facing Message** (GitHub comment):
```
⏸️ **Processing Paused**

I hit the GitHub API rate limit while processing your issue. Your test cases will be 
generated automatically when the limit resets.

Estimated wait: {wait_duration} minutes
Status: Waiting for rate limit reset at {reset_time}

No action needed. I'll continue automatically! ⏰
```

**Action**:
- Calculate wait time until rate limit reset
- Queue job for retry at reset time
- Post comment with wait estimate
- Do not fail job, keep as PENDING

**Recovery**: Auto-resume after rate limit reset

---

### E402: Branch Creation Failed (Permission Denied)

**Severity**: CRITICAL  
**HTTP Status**: 200 OK

**Internal Message**: `Failed to create branch test-cases/issue-{issue_number}: {error}`

**User-Facing Message** (GitHub comment):
```
❌ **Permission Error**

I couldn't create a branch for your test cases due to insufficient permissions.

**Required permissions**:
- ✓ Read repository contents
- ✗ Write repository contents (missing)
- ✗ Create branches (missing)

**How to fix**:
1. Go to repository Settings → Integrations → GitHub App
2. Grant "Contents: Read & Write" permission
3. Re-trigger generation with `/generate-tests`

If you need help, please contact your repository administrator.
```

**Action**:
- Log detailed permission error
- Mark job as FAILED
- Post detailed fix instructions
- Alert repository owner if configured

**Recovery**: Admin grants permissions, user retries

---

### E403: Pull Request Creation Failed

**Severity**: HIGH  
**HTTP Status**: 200 OK (Branch exists, manual PR)

**Internal Message**: `Failed to create PR from branch test-cases/issue-{issue_number}: {error}`

**User-Facing Message** (GitHub comment):
```
⚠️ **Partial Success**

I generated your test cases and committed them to branch `test-cases/issue-{issue_number}`, 
but couldn't create the pull request automatically.

**What you can do**:
1. [Create PR manually]({pr_url}) from branch `test-cases/issue-{issue_number}`
2. Or wait 5 minutes and I'll retry automatically

Test cases are ready in the branch! 🎉
```

**Action**:
- Ensure branch and commit succeeded
- Retry PR creation once after 5 minutes
- Post comment with manual PR link
- Mark job as PARTIALLY_COMPLETE (new status)

**Recovery**: User creates PR manually or auto-retry succeeds

---

### E404: GitHub Comment Posting Failed

**Severity**: LOW  
**HTTP Status**: 200 OK (Log only)

**Internal Message**: `Failed to post comment on issue #{issue_number}: {error}`

**User-Facing Message**: None (primary function succeeded)

**Action**:
- Log error
- Continue processing (PR already created)
- Background retry once
- Do not fail job

**Recovery**: PR link visible in GitHub anyway; low impact

---

### E405: Branch Already Exists

**Severity**: LOW  
**HTTP Status**: 200 OK (Append timestamp)

**Internal Message**: `Branch test-cases/issue-{issue_number} already exists, using test-cases/issue-{issue_number}-{timestamp}`

**User-Facing Message** (GitHub comment):
```
ℹ️ **Note**: Previous test case branch exists. Created new branch: 
`test-cases/issue-{issue_number}-{timestamp}`
```

**Action**:
- Generate unique branch name with timestamp
- Continue processing
- Post comment noting branch name
- Optionally clean up old branch if > 7 days old

**Recovery**: None needed

---

## E5xx: System & Infrastructure Errors

### E501: Redis Cache Unavailable

**Severity**: MEDIUM  
**HTTP Status**: 200 OK (Degraded mode)

**Internal Message**: `Redis connection failed at {redis_url}: {error}, idempotency check skipped`

**User-Facing Message**: None (transparent handling)

**Action**:
- Log error
- Skip idempotency check (risk: possible duplicate PRs)
- Continue processing
- Alert operations team
- Increment degraded mode counter

**Recovery**: Ops team investigates Redis; auto-resume when available

---

### E502: Database Connection Lost

**Severity**: CRITICAL  
**HTTP Status**: 503 Service Unavailable

**Internal Message**: `PostgreSQL connection lost: {error}`

**User-Facing Message**: `Service temporarily unavailable. Please try again in a few minutes.`

**Action**:
- Return 503 (GitHub will retry webhook)
- Attempt connection pool reset
- Page on-call engineer
- Do not create new jobs until connection restored

**Recovery**: Ops team investigates database; GitHub retries webhook

---

### E503: Disk Space Exhausted

**Severity**: CRITICAL  
**HTTP Status**: 503 Service Unavailable

**Internal Message**: `Disk space critically low: {available}MB remaining on {mount_point}`

**User-Facing Message**: `Service temporarily unavailable due to capacity issues.`

**Action**:
- Stop accepting new jobs
- Return 503 for all webhooks
- Trigger emergency cleanup (TTL enforcement)
- Page on-call engineer
- Alert on all channels

**Recovery**: Ops team frees disk space or scales storage

---

### E504: Unexpected System Error

**Severity**: HIGH  
**HTTP Status**: 500 Internal Server Error

**Internal Message**: `Unhandled exception in {component}: {exception_type}: {message}\n{stack_trace}`

**User-Facing Message** (GitHub comment):
```
❌ **Unexpected Error**

Something went wrong while processing your issue. The error has been logged and 
the team has been notified.

**Error ID**: {correlation_id}

Please try again in a few minutes. If this persists, quote the Error ID above when 
reporting the issue.
```

**Action**:
- Log full stack trace with correlation ID
- Post comment with error ID
- Mark job as FAILED
- Alert engineering team with stack trace
- Increment error rate metric

**Recovery**: Engineering team investigates and fixes bug

---

### E505: Job Stuck in PROCESSING

**Severity**: MEDIUM  
**HTTP Status**: N/A (Background check)

**Internal Message**: `Job {job_id} stuck in PROCESSING for {duration} minutes, marking as FAILED`

**User-Facing Message** (GitHub comment):
```
⚠️ **Timeout**

Your test case generation job exceeded the maximum processing time (15 minutes) 
and has been cancelled.

This usually means:
- The issue description was extremely complex
- A temporary system issue occurred

Please try again. If this happens repeatedly, try simplifying your issue description.

**Tip**: Break large features into smaller, focused issues for better test case quality!
```

**Action**:
- Background job monitors ProcessingJob table every 5 minutes
- Find jobs in PROCESSING > 15 minutes
- Mark as FAILED with timeout reason
- Post timeout comment
- Log for investigation

**Recovery**: User retries; ops investigates if pattern

---

## Error Handling Patterns

### Retry Strategy (Exponential Backoff)

```python
retry_delays = [5, 15, 45]  # seconds
max_retries = 3

for attempt in range(1, max_retries + 1):
    try:
        result = operation()
        break
    except RetryableError as e:
        if attempt == max_retries:
            raise MaxRetriesExceeded(e)
        delay = retry_delays[attempt - 1]
        log.warning(f"Retry {attempt}/{max_retries} after {delay}s: {e}")
        time.sleep(delay)
```

### Graceful Degradation Hierarchy

1. **Full functionality**: All services healthy
2. **Degraded mode**: Missing context (E201, E202) - continue without vector DB
3. **Degraded mode**: Missing cache (E501) - skip idempotency check
4. **Delayed mode**: Rate limited (E401) - queue for later
5. **Failed mode**: Critical errors (E502, E503) - reject all requests

### Logging Standards

```python
log.error(
    error_code="E301",
    message="AI generation timeout",
    correlation_id=state.correlation_id,
    issue_number=state.issue_number,
    attempt=retry_count,
    duration_ms=elapsed_time,
    context={
        "issue_title": state.issue_title,
        "similar_cases_count": len(state.similar_cases),
        "prompt_tokens": token_count
    }
)
```

---

## Metrics & Monitoring

**Error Rate Metrics** (by category):
- `errors.webhook.total` (E1xx)
- `errors.vectordb.total` (E2xx)
- `errors.ai.total` (E3xx)
- `errors.github.total` (E4xx)
- `errors.system.total` (E5xx)

**Alert Thresholds**:
- Error rate > 5% in 5 minutes → Warning
- Error rate > 10% in 5 minutes → Critical
- Any E5xx (system errors) → Immediate page

---

**Error Catalog Version**: 1.0  
**Total Error Codes**: 25  
**Last Updated**: 2025-10-26
