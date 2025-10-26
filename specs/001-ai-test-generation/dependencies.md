# External Dependencies: AI Test Case Generation System

**Purpose**: Version requirements, compatibility matrix, and migration strategies  
**Version**: 1.0  
**Date**: 2025-10-26

---

## Dependency Matrix

| Dependency | Version | Type | Compatibility | Migration Strategy | Breaking Change Risk |
|------------|---------|------|---------------|-------------------|---------------------|
| **GitHub API** | v3 (REST) | External API | Stable, LTS | Monitor deprecation notices, 6-month migration window | LOW - Stable API |
| **Llama 3.2** | 3.2.1+ | AI Model | Pin version | Test upgrades in staging, blue-green deployment | MEDIUM - Model behavior changes |
| **ChromaDB** | 0.4.x | Vector Database | Semantic versioning | Backup before upgrade, test queries | MEDIUM - Pre-1.0, evolving API |
| **Redis** | 7.x | Cache | LTS support | Rolling upgrade, backward compatible | LOW - Mature, stable |
| **LangGraph** | 0.2.x | AI Workflow | Pre-1.0, expect breaking changes | Pin version, gradual upgrade with testing | HIGH - Pre-1.0 library |
| **FastAPI** | 0.104+ | Web Framework | Semantic versioning | Minor updates safe, test major versions | LOW - Stable ecosystem |
| **PyGithub** | 2.1+ | GitHub Client | Semantic versioning | Minor updates safe, test compatibility | LOW - Stable library |
| **Python** | 3.11+ | Runtime | LTS (3.11-3.13 supported) | Test on new versions before prod | LOW - Stable language |
| **Ollama** | 0.1.x | Model Server | Pre-1.0, rapid development | Pin version, monitor releases | MEDIUM - Early stage |
| **Cloudflare Tunnel** | latest | Infrastructure | Managed service | Auto-updates, monitor Cloudflare status | LOW - Managed by Cloudflare |

---

## Version Pinning Strategy

### Production Environment

```toml
# pyproject.toml or requirements.txt
python = "^3.11"
fastapi = "0.104.1"  # Pinned for stability
pydantic = "2.5.0"
langchain = "0.1.0"
langgraph = "0.2.3"  # Pin pre-1.0 exactly
chromadb = "0.4.22"  # Pin minor version
redis = "7.2.4"
PyGithub = "2.1.1"
httpx = "0.25.2"
ollama-python = "0.1.7"  # Pin pre-1.0 exactly

# Frontend
react = "18.2.0"
typescript = "5.3.3"
vite = "5.0.8"
tailwindcss = "3.4.0"
```

### Development Environment

```toml
# Allow minor/patch updates for faster iteration
python = "^3.11"
fastapi = "~0.104.0"  # Allow patch updates
langchain = "~0.1.0"
langgraph = "0.2.3"  # Still pin pre-1.0
chromadb = "~0.4.22"
redis = "~7.2.0"
```

---

## GitHub API Details

### Version & Endpoints Used

**API Version**: REST API v3 (stable)  
**Authentication**: GitHub App installation tokens (short-lived)  
**Rate Limits**: 5,000 requests/hour per installation

### Endpoints Used

| Endpoint | Purpose | Rate Limit Impact | Fallback |
|----------|---------|-------------------|----------|
| `GET /repos/{owner}/{repo}` | Verify repository access | Low (once per webhook) | Cache for 1 hour |
| `POST /repos/{owner}/{repo}/git/refs` | Create branch | Medium | N/A - required |
| `PUT /repos/{owner}/{repo}/contents/{path}` | Commit file | High (per file) | Batch commits |
| `POST /repos/{owner}/{repo}/pulls` | Create PR | Medium | Manual PR link |
| `POST /repos/{owner}/{repo}/issues/{number}/comments` | Post comments | High (frequent) | Queue and batch |
| `GET /repos/{owner}/{repo}/issues/{number}` | Fetch issue details | Low (webhook has data) | Use webhook payload |

### Deprecation Monitoring

- **Subscribe to**: GitHub Changelog (https://github.blog/changelog/)
- **Monitor**: API deprecation notices (typically 6-12 months advance notice)
- **Action**: Implement new endpoints in parallel, gradual migration

### Breaking Change Handling

```python
# Example: API version negotiation
headers = {
    "Accept": "application/vnd.github.v3+json",  # Explicit version
    "X-GitHub-Api-Version": "2022-11-28"  # Lock to stable date
}

# Graceful fallback for deprecated endpoints
try:
    response = github_client.create_pull_request(...)
except DeprecatedAPIError:
    log.warning("Using deprecated PR creation endpoint")
    response = github_client.legacy_create_pull_request(...)
```

---

## Llama 3.2 Model Details

### Version & Compatibility

**Model**: Llama 3.2 (Meta AI)  
**Served via**: Ollama 0.1.x  
**Context Window**: 8192 tokens  
**Model Size**: 7B parameters (default) or 70B (optional)

### Version Pinning

```bash
# Dockerfile
FROM ollama/ollama:0.1.22
RUN ollama pull llama3.2:7b-instruct-q4_K_M  # Specific quantization
```

### Model Behavior Consistency

**Problem**: Model updates can change output format/quality  
**Solution**: Pin exact model version and quantization

```python
# backend/src/services/ai/ollama_client.py
OLLAMA_MODEL = "llama3.2:7b-instruct-q4_K_M"  # Pinned
OLLAMA_VERSION = "0.1.22"  # Verified compatible

def verify_model_version():
    """Startup check to ensure correct model is loaded."""
    response = ollama.list()
    if OLLAMA_MODEL not in response.models:
        raise ModelNotFoundError(f"Required model {OLLAMA_MODEL} not found")
```

### Upgrade Strategy

1. **Test in staging**: Load new model alongside old, compare outputs
2. **A/B testing**: Route 10% traffic to new model, monitor quality metrics
3. **Gradual rollout**: Increase to 50%, then 100% over 2 weeks
4. **Rollback plan**: Keep old model loaded, can switch instantly

---

## ChromaDB Vector Database

### Version & API Stability

**Version**: 0.4.x (pre-1.0, evolving)  
**Breaking Change Risk**: MEDIUM - API changes between minor versions  
**Data Format**: Backward compatible within 0.4.x

### API Surface Used

```python
# Core operations (stable within 0.4.x)
collection.add(documents, embeddings, metadatas, ids)
collection.query(query_embeddings, n_results=5)
collection.delete(where={"job_id": job_id})

# Monitor for deprecations
collection.peek()  # May change in 0.5.x
collection.get(where_document={"$contains": "test"})  # Query syntax evolving
```

### Migration Strategy

**Before upgrading minor version (e.g., 0.4.x → 0.5.x)**:

1. **Full backup**: Export all embeddings to JSON
   ```bash
   python scripts/backup_vectordb.py --output backup-2025-10-26.json
   ```

2. **Test in staging**: Load backup into new version, run query tests
   ```python
   # tests/integration/test_vectordb_migration.py
   def test_query_compatibility():
       old_results = old_client.query(embedding, n=5)
       new_results = new_client.query(embedding, n=5)
       assert_similar_results(old_results, new_results, tolerance=0.05)
   ```

3. **Blue-green deployment**: Run both versions temporarily
4. **Validate**: Check query results match (±5% similarity scores acceptable)
5. **Cutover**: Point traffic to new version
6. **Rollback**: Restore from backup if critical issues

### Data Retention & Cleanup

```python
# TTL enforcement (30-day retention)
def cleanup_old_embeddings():
    """Remove embeddings older than 30 days."""
    cutoff_date = datetime.now() - timedelta(days=30)
    collection.delete(
        where={"created_at": {"$lt": cutoff_date.isoformat()}}
    )
```

---

## Redis Cache

### Version & Persistence

**Version**: 7.x (LTS)  
**Persistence**: RDB snapshots + AOF log  
**Use Case**: 1-hour idempotency cache (ephemeral OK)

### Configuration

```conf
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru  # Evict least recently used
save 900 1  # Snapshot every 15 min if 1+ key changed
appendonly yes  # AOF for durability
```

### Upgrade Strategy

**Within 7.x minor versions**: Rolling upgrade (backward compatible)

```bash
# Zero-downtime upgrade
docker-compose exec redis redis-cli CONFIG SET save "900 1"  # Force save
docker-compose up -d --no-deps redis  # Replace container
# Old connections drain, new connections use new version
```

### Failure Handling

**Redis unavailable → Degrade gracefully**:

```python
try:
    cache.get(cache_key)
except RedisConnectionError:
    log.warning("Redis unavailable, skipping idempotency check")
    # Continue without cache (risk: duplicate PRs if webhook redelivery)
    return None  # Treat as cache miss
```

---

## LangGraph Workflow Framework

### Version & Stability

**Version**: 0.2.x (pre-1.0, **HIGH** breaking change risk)  
**API Surface**: State graphs, nodes, edges, conditional routing  
**Breaking Changes**: Expected in 0.3.x, 0.4.x, and 1.0.0

### Pinning Strategy

```toml
langgraph = "==0.2.3"  # Exact pin, no caret
```

**Do NOT auto-upgrade**. Each version change requires:

1. Review changelog for breaking changes
2. Update graph definitions if API changed
3. Full integration test suite
4. Manual testing of workflow

### API Usage (as of 0.2.3)

```python
from langgraph.graph import StateGraph, END

# Current API (may break in 0.3.x)
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("generate", generate_test_cases)
workflow.add_edge("retrieve", "generate")
workflow.add_conditional_edges("generate", route_next_step, {
    "success": "commit",
    "retry": "generate",
    "fail": END
})
```

### Upgrade Testing

```python
# tests/integration/test_langgraph_upgrade.py
def test_workflow_compatibility():
    """Verify workflow still functions after LangGraph upgrade."""
    state = AgentState(issue_number=123, ...)
    result = workflow.invoke(state)
    
    assert result.status == "completed"
    assert result.generated_test_cases is not None
    assert all(stage in result.stages_completed 
               for stage in ["retrieve", "generate", "commit"])
```

---

## Cloudflare Tunnel Infrastructure

### Service Details

**Type**: Managed service (SaaS)  
**SLA**: 99.9% uptime (Cloudflare commitment)  
**Updates**: Auto-applied by Cloudflare  
**Cost**: Free tier (sufficient for ~1000 requests/month)

### Configuration

```yaml
# cloudflared config
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/cert.json
ingress:
  - hostname: test-generator.example.com
    service: http://backend:8000
  - service: http_status:404
```

### Monitoring

**Health Check**: `GET /health` endpoint via tunnel

```python
# backend/src/api/health.py
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "tunnel": "connected",  # Implies tunnel working if request arrives
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Failure Scenarios

| Scenario | Detection | Impact | Recovery |
|----------|-----------|--------|----------|
| Tunnel disconnected | Webhook 502/503 errors | No requests reach backend | Auto-reconnect (30s), GitHub retries |
| Cloudflare outage | Status page | No requests reach backend | Wait for Cloudflare (rare, ~99.9% SLA) |
| Cert expired | Startup failure | Tunnel won't start | Renew cert, restart tunnel |

### Fallback Strategy

**Not applicable** - Cloudflare Tunnel is infrastructure dependency  
**Alternative**: Use ngrok, localhost.run, or port forwarding (dev only)

---

## Dependency Update Schedule

### Regular Updates (Monthly)

- **Python packages**: Patch updates (e.g., 0.104.1 → 0.104.2)
- **Redis**: Patch updates (e.g., 7.2.4 → 7.2.5)
- **Frontend packages**: Patch updates

### Planned Updates (Quarterly)

- **FastAPI, ChromaDB**: Minor updates (e.g., 0.4.22 → 0.4.30)
- **Python**: Minor updates (e.g., 3.11.5 → 3.11.7)

### Major Updates (Requires Planning)

- **LangGraph**: Any version change (test thoroughly)
- **Llama models**: New model versions (A/B test quality)
- **Python**: Major version (e.g., 3.11 → 3.12) - test compatibility
- **ChromaDB**: 0.4.x → 0.5.x or 1.0.0 - migration plan required

---

## Security & CVE Monitoring

### Automated Scanning

```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: snyk/actions/python@master  # Python CVE scan
      - uses: aquasecurity/trivy-action@master  # Container scan
```

### CVE Response Process

1. **Alert received**: Dependabot/Snyk reports vulnerable dependency
2. **Assess severity**: CVSS score, exploitability, exposure
3. **Patch window**:
   - CRITICAL (CVSS 9.0-10): 24 hours
   - HIGH (CVSS 7.0-8.9): 7 days
   - MEDIUM (CVSS 4.0-6.9): 30 days
   - LOW (CVSS 0.1-3.9): Next regular update cycle
4. **Test**: Run full test suite with patched version
5. **Deploy**: Emergency deployment for CRITICAL/HIGH

---

## Deprecation Notices

**Current Deprecations** (as of 2025-10-26): None

**Future Risks**:
- **LangGraph 1.0.0**: Expect major API changes when stable release arrives (~2026)
- **Python 3.11 EOL**: October 2027 (migrate to 3.12+ before then)
- **GitHub API v3**: No deprecation announced, v4 (GraphQL) available as alternative

---

## Dependency Health Dashboard

```bash
# Check for outdated dependencies
poetry show --outdated
npm outdated

# Check for security vulnerabilities
poetry audit
npm audit

# Check for deprecated packages
pyupgrade --py311-plus **/*.py
```

---

**Dependencies Document Version**: 1.0  
**Total External Dependencies**: 10 critical  
**High Risk Dependencies**: 2 (LangGraph, Ollama - pre-1.0)  
**Last Updated**: 2025-10-26
