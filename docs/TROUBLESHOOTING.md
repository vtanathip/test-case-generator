# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the AI Test Case Generator system.

## Table of Contents

- [System Health Checks](#system-health-checks)
- [Webhook Issues](#webhook-issues)
- [AI Generation Issues](#ai-generation-issues)
- [Database Issues](#database-issues)
- [GitHub Integration Issues](#github-integration-issues)
- [Docker Issues](#docker-issues)
- [Performance Issues](#performance-issues)
- [Error Codes Reference](#error-codes-reference)

---

## System Health Checks

### Check All Services Running

```powershell
# View all container statuses
docker-compose ps

# Expected output: All services should show "Up"
# - backend (port 8000)
# - frontend (port 3000)
# - chromadb (port 8000)
# - redis (port 6379)
```

### Check Backend Health

```powershell
# Test health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {"status": "healthy", "version": "0.1.0", ...}
```

### Check Service Logs

```powershell
# View all logs
docker-compose logs -f

# View backend logs only
docker-compose logs -f backend

# Check for errors
docker-compose logs backend --tail=200 | Select-String -Pattern "error|exception|failed"
```

### Check Ollama Connection

```powershell
# Test Ollama is accessible from container
curl http://host.docker.internal:11434/api/tags

# If this fails, Ollama isn't running or accessible
# Solution: Start Ollama service
ollama serve
```

---

## Webhook Issues

### Issue: Webhook Not Received

**Symptoms:**
- Issue created with `generate-tests` label but no workflow starts
- No logs showing webhook received

**Diagnosis:**

```powershell
# Check webhook deliveries in GitHub
# Go to: Settings → Webhooks → Recent Deliveries

# Check backend is listening
docker-compose logs backend | Select-String -Pattern "webhook_received"
```

**Solutions:**

1. **Verify webhook URL is correct:**
   - Should be: `https://your-tunnel-domain/api/webhooks/github`
   - Check cloudflare tunnel is running

2. **Check webhook secret matches:**
   ```powershell
   # In .env file
   GITHUB_WEBHOOK_SECRET=your_secret_here
   
   # Must match GitHub webhook configuration
   ```

3. **Ensure issue has correct label:**
   - Label must be exactly: `generate-tests`
   - System only processes `issues.opened` and `issues.labeled` events

4. **Check GitHub webhook response:**
   - 202 Accepted = Successfully received
   - 409 Conflict = Duplicate (idempotency cache, normal)
   - 400 Bad Request = Invalid signature or unsupported event
   - 500 Internal Server Error = Backend error (check logs)

### Issue: Duplicate Webhook Detected (409 Conflict)

**Symptoms:**
```
"error_code": "E104", "event": "webhook_duplicate_detected"
```

**This is NORMAL behavior!** GitHub sends multiple webhook events:
- Once when issue is opened
- Once when label is added
- Sometimes resends for reliability

The system uses idempotency keys (1-hour cache) to prevent duplicate processing.

**No action needed** - This is working correctly.

---

## AI Generation Issues

### Issue: AI Generation Returns Empty or Very Short Content

**Symptoms:**
- Generated content is 39-100 bytes
- Generation completes in microseconds

**Diagnosis:**

```powershell
# Check logs for generation time
docker-compose logs backend | Select-String -Pattern "stage_generate_completed"

# Should show 20-45 seconds for realistic generation
# If showing milliseconds, there's an error
```

**Solutions:**

1. **Check Ollama is accessible:**
   ```powershell
   # From host
   curl http://localhost:11434/api/tags
   
   # Should list llama3.2:latest model
   ```

2. **Verify model is pulled:**
   ```powershell
   ollama list
   
   # Should show llama3.2:latest
   # If missing: ollama pull llama3.2:latest
   ```

3. **Check Docker host.docker.internal works:**
   ```powershell
   # In .env file
   OLLAMA_HOST=http://host.docker.internal:11434
   
   # NOT http://localhost:11434 (won't work from container)
   ```

4. **Check for method call errors:**
   ```powershell
   docker-compose logs backend | Select-String -Pattern "TypeError|AttributeError"
   
   # Common errors:
   # - "got an unexpected keyword argument 'model'"
   # - "object bool can't be used in 'await' expression"
   ```

### Issue: Embedding Model Not Loaded

**Symptoms:**
```
"error": "Embedding model not loaded"
```

**Diagnosis:**

```powershell
# Check startup logs
docker-compose logs backend | Select-String -Pattern "embedding_model_loaded"

# Should show: {"model": "all-MiniLM-L6-v2", "event": "embedding_model_loaded"}
```

**Solution:**

The embedding model should load automatically on startup. If not:

1. **Rebuild backend:**
   ```powershell
   docker-compose build backend
   docker-compose up -d backend
   ```

2. **Check embedding service initialization in main.py:**
   - Must call `load_model()` after creating `EmbeddingService`

### Issue: Slow AI Generation (>2 minutes)

**Symptoms:**
- Generation takes 3-10 minutes
- High CPU usage

**Diagnosis:**

```powershell
# Check if Ollama is using GPU
ollama ps

# Check resource usage
docker stats
```

**Solutions:**

1. **Use smaller model:**
   ```powershell
   # Pull 3B model (5-10x faster)
   ollama pull llama3.2:3b
   
   # Update .env
   LLAMA_MODEL=llama3.2:3b
   ```

2. **Increase timeout if needed:**
   ```powershell
   # In .env
   OLLAMA_TIMEOUT=180  # 3 minutes
   ```

3. **Check system resources:**
   - Ollama needs 4-8GB RAM
   - Close other heavy applications

---

## Database Issues

### Issue: Vector DB Query Fails

**Symptoms:**
```
"error": "VectorDBClient.query_similar() got an unexpected keyword argument"
```

**Solutions:**

1. **Verify method signature:**
   - Method expects: `query_embedding` (list of floats), `n_results` (int)
   - NOT: `query_text`, `top_k`, `similarity_threshold`

2. **Check embedding generation:**
   ```powershell
   # Logs should show embedding generation before query
   docker-compose logs backend | Select-String -Pattern "embedding_generated"
   ```

### Issue: ChromaDB Telemetry Warning

**Symptoms:**
```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
```

**This is harmless!** It's a ChromaDB library internal issue, not your application.

**No action needed** - Can be safely ignored.

### Issue: Redis Connection Failed

**Symptoms:**
```
"error": "Redis connection failed"
```

**Solutions:**

```powershell
# Check Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

---

## GitHub Integration Issues

### Issue: Branch Creation Fails

**Symptoms:**
```
"error": "GitHubClient.create_branch() missing required positional arguments"
```

**Solution:**

Method requires 3 parameters:
- `repo_full_name`: "owner/repo"
- `branch_name`: "test-cases/issue-N"
- `base_sha`: SHA of branch to branch from

Check logs for actual parameters being passed.

### Issue: File Commit Fails

**Symptoms:**
```
"error": "GitHubClient.create_or_update_file() got an unexpected keyword argument 'path'"
```

**Solution:**

Method parameters are:
- `file_path` (NOT `path`)
- `commit_message` (NOT `message`)
- `repo_full_name`, `content`, `branch`

### Issue: PR Creation Fails

**Symptoms:**
```
"error": "'int' object is not subscriptable"
```

**Solution:**

`create_pull_request()` should return:
```python
{"number": pr.number, "html_url": pr.html_url}
```

NOT just `pr.number` (int).

### Issue: No Comment Added to Issue

**Symptoms:**
- PR created successfully but no comment on issue

**Diagnosis:**

```powershell
docker-compose logs backend | Select-String -Pattern "github_comment_added"

# Should show: {"issue": N, "event": "github_comment_added"}
```

**Solution:**

Check `add_issue_comment()` is being called with correct parameters:
- `repo_full_name` (required)
- `issue_number` (required)
- `comment` (required)

---

## Docker Issues

### Issue: Container Won't Start

**Symptoms:**
- Container exits immediately
- Shows "Exited (1)" status

**Diagnosis:**

```powershell
# Check exit reason
docker-compose logs backend --tail=50

# Common causes:
# - Python syntax errors
# - Missing dependencies
# - Port already in use
```

**Solutions:**

1. **Rebuild container:**
   ```powershell
   docker-compose build --no-cache backend
   docker-compose up -d backend
   ```

2. **Check port conflicts:**
   ```powershell
   # Check if port 8000 is in use
   netstat -ano | findstr :8000
   
   # Kill process if needed
   taskkill /PID <PID> /F
   ```

### Issue: Code Changes Not Applied

**Symptoms:**
- Modified code but behavior unchanged

**Solution:**

**You MUST rebuild the image**, not just restart:

```powershell
# WRONG (doesn't work)
docker-compose restart backend

# CORRECT (rebuilds image with new code)
docker-compose build backend
docker-compose up -d backend
```

Docker bakes your code into the image at build time!

### Issue: Volume Permission Errors

**Symptoms:**
```
"error": "Permission denied"
```

**Solution:**

```powershell
# On Windows: Ensure Docker Desktop has access to drive
# Settings → Resources → File Sharing

# Restart Docker Desktop if needed
```

---

## Performance Issues

### Issue: High Memory Usage

**Diagnosis:**

```powershell
docker stats

# Check memory usage per container
```

**Solutions:**

1. **Increase Docker memory limit:**
   - Docker Desktop → Settings → Resources
   - Allocate 8GB+ RAM

2. **Use smaller AI model:**
   ```powershell
   LLAMA_MODEL=llama3.2:3b  # Needs ~2GB vs 8GB
   ```

3. **Restart containers periodically:**
   ```powershell
   docker-compose restart backend chromadb
   ```

### Issue: Slow Vector DB Queries

**Symptoms:**
- Query takes >2 seconds
- Context retrieval slow

**Solutions:**

1. **Check collection size:**
   ```powershell
   # Large collections (>10k docs) can slow queries
   # Consider pruning old documents
   ```

2. **Verify ChromaDB has enough memory:**
   ```powershell
   docker stats chromadb
   ```

---

## Error Codes Reference

### E101: Invalid Webhook Signature
- **Cause:** HMAC signature verification failed
- **Solution:** Check `GITHUB_WEBHOOK_SECRET` matches GitHub webhook config

### E102: Unsupported Event Type
- **Cause:** Received event other than `issues.opened` or `issues.labeled`
- **Solution:** This is normal for push events, can be ignored

### E103: Missing Required Label
- **Cause:** Issue doesn't have `generate-tests` label
- **Solution:** Add label to issue

### E104: Duplicate Event Detected
- **Cause:** Same webhook event received within 1 hour cache window
- **Solution:** This is normal, prevents duplicate processing

### E201: Vector DB Connection Failed
- **Cause:** ChromaDB not accessible
- **Solution:** Check `docker-compose ps chromadb` and restart if needed

### E202: Vector DB Query Failed
- **Cause:** Error querying similar documents
- **Solution:** Check embedding generation and query parameters

### E301: LLM Connection Failed
- **Cause:** Cannot reach Ollama server
- **Solution:** Check Ollama is running on `http://host.docker.internal:11434`

### E302: LLM Generation Timeout
- **Cause:** AI took longer than configured timeout
- **Solution:** Increase `OLLAMA_TIMEOUT` or use smaller model

### E401: GitHub API Error
- **Cause:** GitHub API request failed
- **Solution:** Check `GITHUB_TOKEN` permissions (needs repo write access)

### E402: Branch Creation Failed
- **Cause:** Branch already exists or permission denied
- **Solution:** Check branch doesn't already exist, verify token permissions

### E403: File Commit Failed
- **Cause:** Cannot create/update file in repository
- **Solution:** Verify branch exists and token has write access

### E404: PR Creation Failed
- **Cause:** Cannot create pull request
- **Solution:** Check base branch exists and token has PR creation permission

---

## Getting Help

If you've tried the solutions above and still have issues:

1. **Check existing issues:** https://github.com/vtanathip/test-case-generator/issues
2. **Create new issue with:**
   - Full error logs (from `docker-compose logs backend --tail=200`)
   - Your `.env` configuration (redact secrets!)
   - Steps to reproduce
   - System information (OS, Docker version)

3. **Enable verbose logging:**
   ```powershell
   # In .env
   LOG_LEVEL=DEBUG
   
   # Rebuild and restart
   docker-compose build backend
   docker-compose up -d backend
   ```

---

**Last Updated:** 2025-10-28  
**Version:** 1.0.0
