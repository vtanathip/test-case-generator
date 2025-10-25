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

### Security Checklist

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
