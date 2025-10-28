# End-to-End Test Cases

This document provides three complete test cases for validating the AI Test Case Generator system from webhook to pull request creation.

## Prerequisites

Before running these test cases, ensure:

- ✅ All Docker services running (`docker-compose ps` shows all "Up")
- ✅ Ollama running locally with llama3.2:latest model
- ✅ GitHub webhook configured and active
- ✅ GitHub token has repo write permissions
- ✅ Backend health check passes: `curl http://localhost:8000/api/health`

---

## Test Case 1: User Authentication Feature

### Objective

Validate the complete workflow for generating test cases for an authentication feature with OAuth2 integration.

### Test Data

**Issue Title:** `Add user authentication with OAuth2`

**Issue Body:**

```markdown
## Feature Description
Implement OAuth2 authentication for users to log in with Google and GitHub accounts.

## Requirements
- Users can click "Login with Google" or "Login with GitHub"
- System redirects to OAuth provider for authorization
- After successful auth, user is redirected back with access token
- Token is stored securely in httpOnly cookie
- Invalid tokens should return 401 Unauthorized
- Expired tokens should trigger automatic refresh

## Technical Details
- Using OAuth2 authorization code flow
- Backend: Node.js + Express
- Frontend: React
- Database: PostgreSQL for user sessions

## Acceptance Criteria
- User can successfully authenticate with Google
- User can successfully authenticate with GitHub
- Invalid credentials are rejected with proper error message
- Session persists across page refreshes
- User can log out and session is cleared
```

### Test Steps

1. **Create GitHub Issue:**
   - Go to https://github.com/vtanathip/test-case-generator/issues/new
   - Enter title and body from test data above
   - Add label: `generate-tests`
   - Click "Submit new issue"
   - Note the issue number (e.g., #20)

2. **Monitor Backend Logs:**

   ```powershell
   docker-compose logs -f backend
   ```

   Expected log sequence:
   - `"event": "webhook_received"` - Webhook accepted
   - `"event": "workflow_started"` - Processing begins
   - `"event": "stage_generate_started"` - AI generation begins
   - `"event": "llm_generated"` - AI completed (20-45 seconds)
   - `"event": "stage_generate_completed"` - Generation stage done
   - `"event": "github_branch_created"` - Branch created
   - `"event": "github_file_created"` - File committed
   - `"event": "github_pr_created"` - PR opened
   - `"event": "github_comment_added"` - Comment added to issue
   - `"event": "workflow_completed"` - Success!

3. **Verify Results:**

   a. **Check issue comment:**
   - Go to the issue page
   - Should see comment: "✅ Test cases have been generated and are ready for review! Pull Request: [link]"

   b. **Check pull request:**
   - Go to https://github.com/vtanathip/test-case-generator/pulls
   - Find PR titled: "Test Cases: Add user authentication with OAuth2"
   - Base branch: `main`
   - Head branch: `test-cases/issue-20` (or your issue number)

   c. **Check generated content:**
   - Open the PR and view files changed
   - Should contain file: `test-cases/issue-20.md`
   - Verify content includes:
     - Test cases for Google OAuth login
     - Test cases for GitHub OAuth login
     - Token validation test cases
     - Session management test cases
     - Error handling test cases

### Expected Results

- ✅ Total execution time: 30-60 seconds
- ✅ Generated content: 3,000-6,000 bytes
- ✅ Test cases cover all requirements from issue body
- ✅ Test cases follow structured format (Objective, Preconditions, Steps, Expected Results)
- ✅ Edge cases and security tests included
- ✅ No errors in backend logs

### Pass Criteria

- Pull request created successfully
- Test case file contains 5+ test cases
- All test cases relate to OAuth2 authentication
- Issue has comment with PR link
- No errors in workflow execution

---

## Test Case 2: REST API Endpoint

### Objective

Validate test case generation for a backend API endpoint with request validation and error handling.

### Test Data

**Issue Title:** `Create REST API endpoint for user profile updates`

**Issue Body:**

```markdown
## Endpoint Specification

### `PATCH /api/users/:userId/profile`

Updates user profile information.

## Request Body

```json
{
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "bio": "string (max 500 chars)",
  "avatarUrl": "string (valid URL)"
}
```

## Response

**200 OK:**
```json
{
  "id": "uuid",
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "bio": "string",
  "avatarUrl": "string",
  "updatedAt": "ISO8601 datetime"
}
```

**400 Bad Request:**
- Invalid email format
- Bio exceeds 500 characters
- Invalid avatar URL

**401 Unauthorized:**
- Missing authentication token
- Invalid token

**403 Forbidden:**
- User trying to update another user's profile

**404 Not Found:**
- User ID doesn't exist

**429 Too Many Requests:**
- Rate limit exceeded (10 requests per minute)

## Technical Requirements
- Authentication: JWT Bearer token
- Rate limiting: 10 req/min per user
- Input validation: All fields optional, but must be valid if provided
- Database: PostgreSQL with user table
```

### Test Steps

1. **Create GitHub Issue:**
   - Create issue with title and body from test data
   - Add label: `generate-tests`
   - Submit and note issue number

2. **Monitor Processing:**

   ```powershell
   # Watch for completion
   docker-compose logs -f backend | Select-String -Pattern "workflow_completed|workflow_failed"
   ```

3. **Verify Generated Test Cases Cover:**
   - ✅ Happy path (valid request, 200 OK)
   - ✅ Input validation (400 errors)
   - ✅ Authentication (401 errors)
   - ✅ Authorization (403 errors)
   - ✅ Not found (404 errors)
   - ✅ Rate limiting (429 errors)
   - ✅ Edge cases (empty fields, max length, special characters)
   - ✅ Concurrent updates
   - ✅ Partial updates (only some fields)

### Expected Results

- ✅ Execution time: 30-60 seconds
- ✅ Generated content: 4,000-7,000 bytes
- ✅ Test cases include example request/response bodies
- ✅ Test cases cover all HTTP status codes mentioned
- ✅ Security test cases included

### Pass Criteria

- 10+ test cases generated
- All status codes (200, 400, 401, 403, 404, 429) covered
- Input validation scenarios included
- Rate limiting scenario included
- Authentication/authorization tests present

---

## Test Case 3: Database Migration

### Objective

Validate test case generation for a database schema change with data integrity requirements.

### Test Data

**Issue Title:** `Add email verification status to users table`

**Issue Body:**

```markdown
## Migration Requirements

Add email verification tracking to existing users table.

## Schema Changes

### New Columns

```sql
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(255);
ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP;
ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP;
```

### Indexes

```sql
CREATE INDEX idx_users_email_verified ON users(email_verified);
CREATE INDEX idx_users_verification_token ON users(email_verification_token);
```

## Data Migration

- All existing users: Set `email_verified = TRUE` (grandfather clause)
- Set `email_verified_at = created_at` for existing users
- New users after migration: `email_verified = FALSE` by default

## Rollback Strategy

```sql
ALTER TABLE users DROP COLUMN email_verified;
ALTER TABLE users DROP COLUMN email_verification_token;
ALTER TABLE users DROP COLUMN verification_sent_at;
ALTER TABLE users DROP COLUMN email_verified_at;
```

## Testing Requirements

- Verify migration runs without errors
- Verify existing users marked as verified
- Verify new users created after migration are not verified
- Verify indexes created successfully
- Verify rollback works correctly
- Verify application code works with new schema
- Test performance impact of new indexes
```

### Test Steps

1. **Create GitHub Issue:**
   - Create issue with migration specifications
   - Add label: `generate-tests`
   - Submit issue

2. **Monitor for Vector DB Context:**

   ```powershell
   docker-compose logs backend | Select-String -Pattern "context_count"
   ```

   If previous test cases were processed, this should show `context_count > 0`, meaning the AI is learning from previous tests!

3. **Verify Generated Test Cases Cover:**
   - ✅ Migration execution (forward)
   - ✅ Data integrity for existing records
   - ✅ Default values for new records
   - ✅ Index creation verification
   - ✅ Rollback migration
   - ✅ Application compatibility
   - ✅ Performance impact
   - ✅ Concurrent operations during migration
   - ✅ Foreign key constraints (if any)
   - ✅ Data validation

### Expected Results

- ✅ Execution time: 30-60 seconds
- ✅ Generated content: 3,500-6,500 bytes
- ✅ Test cases include SQL queries for verification
- ✅ Both forward and rollback migrations tested
- ✅ Data integrity checks included

### Pass Criteria

- 8+ test cases generated
- Migration execution tested
- Rollback scenario included
- Data integrity verification present
- Performance testing mentioned
- Test cases reference SQL queries

---

## Common Validation Steps

For all test cases above, perform these common validations:

### 1. Check Workflow Status

```powershell
# Should show COMPLETED
docker-compose logs backend | Select-String -Pattern "final_status"
```

### 2. Check for Errors

```powershell
# Should return no matches (or only harmless ChromaDB telemetry)
docker-compose logs backend --tail=200 | Select-String -Pattern "workflow_failed|error.*workflow"
```

### 3. Validate PR Structure

- Title format: `Test Cases: [Issue Title]`
- Branch format: `test-cases/issue-[N]`
- File format: `test-cases/issue-[N].md`
- Base branch: `main`

### 4. Validate Content Quality

- Test cases have clear titles
- Each test has Objective, Preconditions, Steps, Expected Results
- Edge cases are included
- Security considerations mentioned (if relevant)
- Test data examples provided

### 5. Check Vector DB Learning

After running all 3 test cases:

```powershell
# Check if system is finding context from previous runs
docker-compose logs backend | Select-String -Pattern "context_count" | Select-Object -Last 5
```

Expected progression:
- First test: `"context_count": 0` (no history)
- Second test: `"context_count": 1-5` (learning from first)
- Third test: `"context_count": 5-10` (learning from both previous)

---

## Performance Benchmarks

### Expected Timing (per test case)

| Stage | Target Time | Acceptable Range |
|-------|-------------|------------------|
| Webhook → Start | <1 second | <3 seconds |
| Generate Embedding | <1 second | <3 seconds |
| Query Vector DB | <1 second | <3 seconds |
| AI Generation | 20-35 seconds | 15-60 seconds |
| Create Branch | 1-2 seconds | <5 seconds |
| Commit File | 1-2 seconds | <5 seconds |
| Create PR | 1-3 seconds | <10 seconds |
| Add Comment | 1-2 seconds | <5 seconds |
| **Total** | **30-50 seconds** | **25-90 seconds** |

### Content Quality Benchmarks

| Metric | Target | Minimum |
|--------|--------|---------|
| Content Size | 3,000-6,000 bytes | 2,000 bytes |
| Test Case Count | 5-12 test cases | 3 test cases |
| Coverage | All requirements | 70% of requirements |
| Edge Cases | 2-4 edge cases | 1 edge case |
| Security Tests | 1-3 security tests | 1 (if relevant) |

---

## Troubleshooting Test Failures

### If Workflow Fails

1. **Check logs for specific error:**

   ```powershell
   docker-compose logs backend --tail=100 | Select-String -Pattern "error|exception"
   ```

2. **Common issues:**
   - Ollama not running → Start Ollama service
   - Embedding model not loaded → Rebuild backend
   - GitHub token expired → Update token in .env
   - Rate limit exceeded → Wait and retry

3. **Refer to:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

### If Content Quality Poor

1. **Check AI generation time:**
   - <5 seconds = Error occurred, check logs
   - 5-15 seconds = Model too small or issue description too short
   - >60 seconds = System overloaded or network issues

2. **Improve issue description:**
   - Add more technical details
   - Include acceptance criteria
   - Specify edge cases explicitly
   - Provide example data

3. **Let vector DB learn:**
   - First few test cases may be generic
   - Quality improves as system learns patterns
   - After 5-10 issues, should see significant improvement

---

## Success Metrics

All three test cases should pass with:

- ✅ 100% workflow completion rate (3/3 succeeded)
- ✅ Average execution time: 30-60 seconds
- ✅ Average content size: 3,500-6,000 bytes
- ✅ All PRs created successfully
- ✅ All issues commented with PR links
- ✅ No errors in logs
- ✅ Vector DB learning from previous tests (context_count increasing)

---

**Last Updated:** 2025-10-28  
**Version:** 1.0.0
