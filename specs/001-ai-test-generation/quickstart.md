# Quickstart Guide: AI Test Case Generation System

**Last Updated**: 2025-10-25  
**Estimated Setup Time**: 15 minutes

## Prerequisites

- Docker Desktop 24.0+ and Docker Compose 2.20+
- GitHub account with repository access
- Local server with GPU (recommended: NVIDIA GPU with 8GB+ VRAM for Llama 3.2 11B)
- Cloudflare account (for tunnel setup)

**Note**: For systems without GPU, Llama 3.2 can run on CPU but will be slower (5-10x). Consider using the smaller Llama 3.2 3B variant for CPU-only setups.

## Quick Start (MVP)

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/owner/test-case-generator.git
cd test-case-generator

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required variables:
#   GITHUB_TOKEN=ghp_xxx           # GitHub personal access token
#   GITHUB_WEBHOOK_SECRET=xxx      # Webhook secret (you'll create this)
#   LLAMA_MODEL=llama3.2:11b       # Llama model variant (11b or 90b)
#   OLLAMA_HOST=ollama             # Ollama server hostname
#   CLOUDFLARE_TUNNEL_TOKEN=xxx    # Cloudflare tunnel token
```

### 2. Start Services

```bash
# Start all services (backend, frontend, ChromaDB, Redis, Ollama)
docker-compose up -d

# Pull Llama 3.2 model (first time only, may take 5-10 minutes)
docker-compose exec ollama ollama pull llama3.2:11b

# Check service health
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Configure GitHub Webhook

1. Go to your GitHub repository → Settings → Webhooks → Add webhook
2. **Payload URL**: `https://your-tunnel-domain.trycloudflare.com/webhooks/github`
3. **Content type**: `application/json`
4. **Secret**: Use the value from `GITHUB_WEBHOOK_SECRET` in `.env`
5. **Events**: Select "Issues" only
6. **Active**: Check the box
7. Save webhook

### 4. Create Test Issue

```bash
# In your GitHub repository, create a new issue:
# Title: "Add user authentication feature"
# Body: "Implement OAuth2 authentication with Google provider. Support login, logout, and token refresh."
# Labels: Add "generate-tests" tag

# Within 2 minutes, check:
# - Dashboard at http://localhost:3000
# - New PR should appear in your repository
```

### 5. Access Dashboard

Open browser to `http://localhost:3000`

You should see:

- **Processing Stats**: Total issues, success rate, avg processing time
- **Recent Issues**: List of issues with status (PENDING, PROCESSING, COMPLETED)
- **Generated Test Cases**: Grid of test case documents with PR links
- **System Health**: Vector DB size, cache hit rate, component status

## Detailed Setup

### Environment Variables

Create `.env` file with all required configuration:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx          # Repo access token with write permissions
GITHUB_WEBHOOK_SECRET=your_secret_here  # Webhook signature secret (random string)
GITHUB_REPO=owner/repo                  # Repository full name

# Llama 3.2 Configuration
LLAMA_MODEL=llama3.2:11b                # Model variant (3b, 11b, or 90b)
OLLAMA_HOST=ollama                      # Ollama hostname (docker service name)
OLLAMA_PORT=11434                       # Ollama API port
OLLAMA_GPU_LAYERS=33                    # Number of layers to offload to GPU (-1 for all)

# Embedding Model Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2        # Sentence-transformers model for embeddings
EMBEDDING_DIMENSION=384                 # Embedding vector dimension

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=xxxxx           # Tunnel authentication token

# Redis Configuration
REDIS_HOST=redis                        # Redis hostname (docker service name)
REDIS_PORT=6379                         # Redis port
REDIS_DB=0                              # Redis database number

# ChromaDB Configuration
CHROMADB_HOST=chromadb                  # ChromaDB hostname (docker service name)
CHROMADB_PORT=8000                      # ChromaDB port

# Application Configuration
LOG_LEVEL=INFO                          # Logging level (DEBUG, INFO, WARNING, ERROR)
MAX_RETRIES=3                           # Max AI generation retries
RETRY_DELAYS=5,15,45                    # Retry delays in seconds (exponential backoff)
VECTOR_RETENTION_DAYS=30                # Vector DB retention period
CACHE_TTL_SECONDS=3600                  # Idempotency cache TTL (1 hour)
MAX_ISSUE_BODY_LENGTH=5000              # Max issue description length
LLM_TIMEOUT_SECONDS=120                 # Llama generation timeout (longer for local inference)
```

### Docker Compose Services

The `docker-compose.yml` file defines 5 services:

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment: [all env vars from .env]
    depends_on: [redis, chromadb, ollama]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      REACT_APP_API_URL: http://localhost:8000

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["./data/ollama:/root/.ollama"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  chromadb:
    image: chromadb/chroma:latest
    ports: ["8001:8000"]
    volumes: ["./data/chromadb:/chroma/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: ["redis-server", "--maxmemory", "256mb", "--maxmemory-policy", "allkeys-lru"]
```

**GPU Requirements**:

- Llama 3.2 11B: Requires ~8GB VRAM
- Llama 3.2 90B: Requires ~48GB VRAM (multi-GPU or quantized)
- Llama 3.2 3B: Requires ~4GB VRAM (CPU fallback possible)

**CPU-Only Mode**:

If no GPU available, update `docker-compose.yml`:

```yaml
ollama:
  image: ollama/ollama:latest
  environment:
    OLLAMA_NUM_GPU: 0  # Disable GPU, use CPU only
```

### GitHub Token Permissions

Create a GitHub Personal Access Token with these scopes:

- `repo` - Full control of private repositories
  - `repo:status` - Access commit status
  - `repo_deployment` - Access deployment status
  - `public_repo` - Access public repositories
- `write:discussion` - Write access to discussions

**Steps**:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Select scopes above
4. Copy token (shown only once)
5. Add to `.env` as `GITHUB_TOKEN`

### Cloudflare Tunnel Setup

1. Install `cloudflared` CLI:

   ```bash
   # macOS
   brew install cloudflare/cloudflare/cloudflared

   # Linux
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared-linux-amd64.deb
   ```

2. Authenticate:

   ```bash
   cloudflared tunnel login
   ```

3. Create tunnel:

   ```bash
   cloudflared tunnel create test-case-generator
   # Copy tunnel ID from output
   ```

4. Configure tunnel:

   Create `~/.cloudflared/config.yml`:

   ```yaml
   tunnel: <TUNNEL_ID>
   credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

   ingress:
     - hostname: test-gen.your-domain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

5. Start tunnel:

   ```bash
   cloudflared tunnel run test-case-generator
   ```

6. Add tunnel token to `.env`:

   ```bash
   CLOUDFLARE_TUNNEL_TOKEN=<TOKEN_FROM_TUNNEL_CREATION>
   ```

### Initial Vector DB Seeding (Optional)

To pre-populate vector database with example test cases:

```bash
# Run seeding script
docker-compose exec backend python scripts/seed_vector_db.py

# This will:
# - Load example test cases from /seed-data/
# - Generate embeddings using OpenAI
# - Store in ChromaDB
# - Verify retrieval works
```

## Development Workflow

### Running Tests

```bash
# Run all tests
docker-compose exec backend pytest

# Run unit tests only
docker-compose exec backend pytest tests/unit/

# Run with coverage
docker-compose exec backend pytest --cov=src --cov-report=html

# View coverage report
open backend/htmlcov/index.html
```

### Local Development (Without Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
npm start
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# With timestamps
docker-compose logs -f --timestamps backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Database Inspection

```bash
# Redis CLI
docker-compose exec redis redis-cli

# List all keys
KEYS *

# Get cache entry
GET webhook:42:issues.opened:1729858800

# Check TTL
TTL webhook:42:issues.opened:1729858800

# ChromaDB inspection (via Python)
docker-compose exec backend python
>>> import chromadb
>>> client = chromadb.Client()
>>> collection = client.get_collection("test_cases")
>>> collection.count()  # Number of embeddings
```

## Troubleshooting

### Webhook Not Triggering

1. Check Cloudflare tunnel is running:

   ```bash
   curl https://your-tunnel-domain.trycloudflare.com/api/health
   ```

2. Verify webhook signature secret matches:

   ```bash
   # In .env file
   echo $GITHUB_WEBHOOK_SECRET

   # In GitHub webhook settings (must match)
   ```

3. Check backend logs for signature validation errors:

   ```bash
   docker-compose logs backend | grep "signature"
   ```

### AI Generation Failing

1. Verify Ollama is running and model is pulled:

   ```bash
   # Check Ollama health
   curl http://localhost:11434/api/tags

   # Test model generation
   curl http://localhost:11434/api/generate -d '{
     "model": "llama3.2:11b",
     "prompt": "Test prompt"
   }'
   ```

2. Check GPU availability:

   ```bash
   # Inside ollama container
   docker-compose exec ollama nvidia-smi

   # Check GPU usage during generation
   watch -n 1 nvidia-smi
   ```

3. Increase timeout if generation is slow:

   ```bash
   # In .env
   LLM_TIMEOUT_SECONDS=180  # 3 minutes for slower hardware
   ```

4. Switch to smaller model if memory issues:

   ```bash
   # In .env
   LLAMA_MODEL=llama3.2:3b  # Smaller, faster model
   ```

### Vector DB Issues

1. Reset ChromaDB (WARNING: deletes all embeddings):

   ```bash
   docker-compose down
   rm -rf data/chromadb/*
   docker-compose up -d
   ```

2. Check ChromaDB connection:

   ```bash
   curl http://localhost:8001/api/v1/heartbeat
   ```

### Dashboard Not Loading

1. Check frontend logs:

   ```bash
   docker-compose logs frontend
   ```

2. Verify API URL:

   ```bash
   # In frontend/.env
   REACT_APP_API_URL=http://localhost:8000

   # Test API endpoint
   curl http://localhost:8000/api/stats
   ```

## Production Deployment

### Security Setup (Required for Production)

#### 1. Secret Storage (FR-018: Environment Variable Security)

**Requirement**: Store all secrets in environment variables, never in code or logs

**Setup**:

```bash
# DO NOT commit .env file to git
echo ".env" >> .gitignore

# Use secret management service in production
# Option A: Docker Secrets (Swarm mode)
echo "ghp_xxxxxxxxxxxxx" | docker secret create github_token -

# Option B: Kubernetes Secrets
kubectl create secret generic app-secrets \
  --from-literal=github-token=ghp_xxxxxxxxxxxxx \
  --from-literal=webhook-secret=your_secret_here

# Option C: HashiCorp Vault (recommended for enterprise)
vault kv put secret/test-generator/github \
  token=ghp_xxxxxxxxxxxxx \
  webhook_secret=your_secret_here
```

**Validation**:

```bash
# Verify secrets are NOT in code
grep -r "ghp_" backend/src/  # Should return empty
grep -r "webhook_secret" backend/src/  # Should only show env var references

# Verify logs are sanitized (FR-021)
docker-compose logs backend | grep "ghp_"  # Should return empty
docker-compose logs backend | grep "Authorization"  # Should show "[REDACTED]"
```

#### 2. Secret Rotation (FR-019: 24-Hour Grace Period)

**Requirement**: Support graceful secret rotation with 24-hour overlap period

**Rotation Procedure**:

```bash
# Step 1: Generate new GitHub token
# GitHub → Settings → Developer settings → Personal access tokens → Generate new token

# Step 2: Add new token to environment with "_NEW" suffix
export GITHUB_TOKEN_NEW=ghp_yyyyyyyyyyyy  # New token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx     # Old token (still valid)

# Step 3: Update application to accept both tokens (24-hour grace period)
# Application automatically checks both GITHUB_TOKEN and GITHUB_TOKEN_NEW

# Step 4: Update webhook secret in GitHub repository
# GitHub → Repository → Settings → Webhooks → Edit → Update secret

# Step 5: Wait 24 hours for all in-flight requests to complete

# Step 6: Promote new token to primary (after 24 hours)
export GITHUB_TOKEN=ghp_yyyyyyyyyyyy      # Promote new to primary
unset GITHUB_TOKEN_NEW                     # Remove old token

# Step 7: Revoke old token in GitHub
# GitHub → Settings → Personal access tokens → Revoke old token
```

**Automated Rotation** (cron job):

```bash
# Add to crontab (run monthly on 1st at 2 AM UTC)
0 2 1 * * /usr/local/bin/rotate-secrets.sh

# rotate-secrets.sh contents:
#!/bin/bash
set -e

# Generate new token via GitHub API (requires admin token)
NEW_TOKEN=$(curl -X POST -H "Authorization: token $ADMIN_TOKEN" \
  https://api.github.com/applications/CLIENT_ID/token \
  -d '{"scopes":["repo"]}' | jq -r .token)

# Set new token with grace period
docker exec backend env GITHUB_TOKEN_NEW=$NEW_TOKEN

# Schedule old token removal after 24 hours
echo "unset GITHUB_TOKEN_NEW" | at now + 24 hours
```

#### 3. Rate Limiting (FR-020: 100 req/min per Repository)

**Requirement**: Enforce rate limit of 100 webhooks/minute per repository

**Setup** (nginx rate limiting):

```nginx
# Add to nginx.conf or Cloudflare Worker
http {
    # Define rate limit zone: 100 requests/min per repo
    limit_req_zone $repo_name zone=repo_limit:10m rate=100r/m;

    server {
        location /webhooks/github {
            # Extract repository name from webhook payload
            set $repo_name $http_x_github_repo;
            
            # Apply rate limit
            limit_req zone=repo_limit burst=20 nodelay;
            limit_req_status 429;

            # Forward to backend
            proxy_pass http://backend:8000;
        }
    }
}
```

**Validation**:

```bash
# Test rate limit with burst of requests
for i in {1..150}; do
  curl -X POST http://localhost:8000/webhooks/github \
    -H "X-GitHub-Repo: owner/repo" \
    -H "Content-Type: application/json" \
    -d '{"action":"labeled"}' &
done
wait

# Check rate limit responses (should see HTTP 429 after 120 requests)
docker-compose logs backend | grep "429" | wc -l  # Should show ~30 rejected
```

#### 4. Log Sanitization (FR-021: Mask Secrets in Logs)

**Requirement**: Sanitize logs to prevent secret leakage

**Implementation** (backend logging configuration):

```python
# backend/src/core/logging.py
import logging
import re

class SanitizingFormatter(logging.Formatter):
    """Formatter that redacts secrets from log messages"""
    
    PATTERNS = [
        (re.compile(r'ghp_[a-zA-Z0-9]{36}'), '[REDACTED_GITHUB_TOKEN]'),
        (re.compile(r'sha256=[a-f0-9]{64}'), '[REDACTED_WEBHOOK_SIGNATURE]'),
        (re.compile(r'Authorization: Bearer .+'), 'Authorization: Bearer [REDACTED]'),
        (re.compile(r'"token":\s*"[^"]+"'), '"token": "[REDACTED]"'),
        (re.compile(r'"secret":\s*"[^"]+"'), '"secret": "[REDACTED]"'),
    ]
    
    def format(self, record):
        msg = super().format(record)
        for pattern, replacement in self.PATTERNS:
            msg = pattern.sub(replacement, msg)
        return msg
```

**Validation Examples**:

```bash
# Test log sanitization
curl -X POST http://localhost:8000/webhooks/github \
  -H "X-Hub-Signature-256: sha256=abc123..." \
  -H "Authorization: Bearer ghp_xxxxxxxxxxxxx"

# Check logs show redacted values
docker-compose logs backend | tail -20
# Expected output:
#   INFO: Received webhook with signature=[REDACTED_WEBHOOK_SIGNATURE]
#   INFO: GitHub API request with token=[REDACTED_GITHUB_TOKEN]
```

#### 5. TLS Configuration (FR-022: TLS 1.2+ via Cloudflare Tunnel)

**Requirement**: All external connections use TLS 1.2 or higher

**Cloudflare Tunnel Setup**:

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Authenticate with Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create test-generator

# Configure tunnel (save to ~/.cloudflared/config.yml)
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: test-generator.yourdomain.com
    service: http://localhost:8000
    originRequest:
      noTLSVerify: false  # Enforce TLS verification
  - service: http_status:404

# Route DNS
cloudflared tunnel route dns test-generator test-generator.yourdomain.com

# Run tunnel (or add to systemd)
cloudflared tunnel run test-generator
```

**TLS Validation**:

```bash
# Verify TLS 1.2+ is enforced
curl -v --tlsv1.1 https://test-generator.yourdomain.com/health 2>&1 | grep "SSL"
# Expected: Connection refused (TLS 1.1 rejected)

curl -v --tlsv1.2 https://test-generator.yourdomain.com/health 2>&1 | grep "SSL"
# Expected: Success (TLS 1.2 accepted)

# Check TLS configuration
nmap --script ssl-enum-ciphers -p 443 test-generator.yourdomain.com
# Expected output:
#   TLSv1.2:
#     ciphers:
#       TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 (secp256r1) - A
#       TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 (secp256r1) - A
```

#### 6. Incident Response Procedures (FR-023)

**Requirement**: Documented procedures for security incidents

**Incident Response Plan**:

### Phase 1: Detection and Assessment (0-15 minutes)

1. Alert triggered (e.g., unauthorized access attempt, token leak)
2. Assess severity: CRITICAL (token leaked), HIGH (suspicious activity), MEDIUM (rate limit breach)
3. Notify security team via PagerDuty/Slack

### Phase 2: Containment (15-30 minutes)

**Token Leak**: Immediately revoke compromised token in GitHub

```bash
# GitHub → Settings → Personal access tokens → Revoke token ghp_xxxxxxxxxxxxx
```

**Rotate webhook secret**:

```bash
# Generate new secret
NEW_SECRET=$(openssl rand -hex 32)
# Update in GitHub webhook settings
# Update GITHUB_WEBHOOK_SECRET in .env
docker-compose restart backend
```

**Block malicious IPs**:

```bash
# Add to nginx/Cloudflare firewall
iptables -A INPUT -s <MALICIOUS_IP> -j DROP
```

### Phase 3: Audit and Investigation (30 minutes - 2 hours)

1. Check audit logs for suspicious activity:

   ```bash
   # Search logs for unauthorized access
   docker-compose logs backend | grep "401\|403\|Invalid signature"
   
   # Export logs for forensic analysis
   docker-compose logs --since 24h backend > incident-logs-$(date +%Y%m%d).txt
   ```

2. Review GitHub audit log (Settings → Security → Audit log)
3. Check vector DB for unauthorized queries
4. Verify no data exfiltration (check outbound network traffic)

### Phase 4: Recovery (2-4 hours)

1. Generate new secrets (token, webhook secret, Redis password)
2. Deploy with new secrets (24-hour grace period)
3. Verify system integrity (run health checks, test workflows)
4. Monitor for 24 hours for repeat incidents

### Phase 5: Post-Incident (1-2 days)

1. Document incident timeline and impact
2. Update security policies if needed
3. Conduct blameless postmortem with team
4. Update runbook with lessons learned

**Contact List**:

```text
Security Lead: security-lead@company.com
On-Call Engineer: oncall@company.com
GitHub Admin: github-admin@company.com
Incident Response Slack: #security-incidents
PagerDuty Escalation: https://company.pagerduty.com/escalation_policies/P123456
```

### Security Checklist (Pre-Production)

- [ ] Use GitHub App authentication (not personal token)
- [ ] Enable webhook signature validation (verify `GITHUB_WEBHOOK_SECRET` set)
- [ ] Use HTTPS for all endpoints (Cloudflare tunnel handles this)
- [ ] Store secrets in vault (not `.env` file)
- [ ] Enable Redis AUTH (`requirepass` in redis.conf)
- [ ] Restrict ChromaDB access (network policies)
- [ ] Set up monitoring alerts (error rates, latency)
- [ ] Configure log aggregation (e.g., Grafana Loki)

### Scaling Considerations

- **Horizontal scaling**: Run multiple backend instances behind load balancer
- **Vector DB**: Migrate to Qdrant for production scale (>10k embeddings)
- **Cache**: Use Redis Cluster for high availability
- **Monitoring**: Add Prometheus metrics + Grafana dashboards
- **Rate limiting**: Implement per-repository rate limits

## Next Steps

1. Read [data-model.md](./data-model.md) for entity details
2. Review [OpenAPI spec](./contracts/openapi.yaml) for API contracts
3. Check [research.md](./research.md) for technology decisions
4. Proceed to `/speckit.tasks` for implementation task breakdown

## Support

- **Issues**: <https://github.com/owner/test-case-generator/issues>
- **Documentation**: [Main README](../../../README.md)
- **Constitution**: [.specify/memory/constitution.md](../../../.specify/memory/constitution.md)
