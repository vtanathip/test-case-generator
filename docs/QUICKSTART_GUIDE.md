# 🚀 Quick Start Guide - Core MVP

**Estimated Setup Time**: 10-15 minutes

## ✅ What's Already Done

Your Docker services are running:
- ✅ Backend (FastAPI) - Port 8000
- ✅ Frontend (React) - Port 3000  
- ✅ Ollama (Llama 3.2) - Port 11434
- ✅ ChromaDB (Vector DB) - Port 8001
- ✅ Redis (Cache) - Port 6379
- ✅ Llama 3.2 model downloaded (2GB)

## 📝 Configuration Required

### Step 1: Get GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: `test-case-generator`
4. Select scopes:
   - ✅ **repo** (Full control of repositories)
   - ✅ **admin:repo_hook** (Manage webhooks)
5. Click "Generate token"
6. **COPY THE TOKEN** (starts with `ghp_` or `github_pat_`)

### Step 2: Update .env File

Open `.env` and update these 3 variables:

```bash
# Replace this with your actual token from Step 1
GITHUB_TOKEN=ghp_YOUR_ACTUAL_TOKEN_HERE

# Already generated for you (keep this)
GITHUB_WEBHOOK_SECRET=hjOb7Kg0BL5pDnl1FSv2Tqzf4QRHY6JU

# Already set to your repo (keep this)
GITHUB_REPO=vtanathip/test-case-generator
```

**⚠️ IMPORTANT**: Replace `GITHUB_TOKEN` with your actual token!

### Step 3: Restart Backend

After updating `.env`:

```powershell
docker-compose restart backend
```

Wait ~10 seconds, then verify:

```powershell
Invoke-WebRequest -Uri http://localhost:8000/api/health
```

Should return: `{"status":"healthy",...}`

---

## 🌐 Exposing Backend with Cloudflare Quick Tunnel (Experimental)

For testing GitHub webhooks without production deployment:

### Install cloudflared

Download from: https://github.com/cloudflare/cloudflared/releases/latest

```powershell
# Verify installation
cloudflared --version
```

### Start Quick Tunnel

```powershell
# Expose backend on port 8000
cloudflared tunnel --url http://localhost:8000
```

**Output will show**:
```
Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
https://random-words-1234.trycloudflare.com
```

**⚠️ Important Notes**:
- URL changes every time you restart the tunnel
- You'll need to manually update GitHub webhook URL after each restart
- **For experimental use only** - use Named Tunnel for production
- Keep terminal open while testing webhooks

### Configure GitHub Webhook

1. Go to: `https://github.com/vtanathip/test-case-generator/settings/hooks`
2. Click "Add webhook"
3. **Payload URL**: `https://YOUR-TUNNEL-URL.trycloudflare.com/api/webhooks/github` (replace with actual tunnel URL)
4. **Content type**: `application/json`
5. **Secret**: Copy `GITHUB_WEBHOOK_SECRET` from your `.env` file
6. **Events**: Select "Let me select individual events" → Check only "Issues"
7. Click "Add webhook"

### Test Webhook Connection

Create a test issue with the `generate-tests` label:

1. Go to: `https://github.com/vtanathip/test-case-generator/issues/new`
2. Title: `Test webhook integration`
3. Body: `This is a test issue to verify webhook connectivity. The system should generate test cases for this feature.`
4. Labels: Add `generate-tests`
5. Click "Submit new issue"

Check backend logs:
```powershell
docker-compose logs -f backend
```

You should see webhook processing logs with correlation ID.

**🔄 Remember**: If you restart `cloudflared`, update the webhook URL in GitHub settings!

---

## 🧪 Testing the MVP (Without GitHub Webhooks)

Alternatively, you can test the core functionality locally using the API directly without exposing via tunnel.

### Test 1: Manual Webhook Simulation

Create a test file `test-webhook.json`:

```json
{
  "action": "opened",
  "issue": {
    "number": 123,
    "title": "Add user authentication",
    "body": "Implement OAuth2 authentication with Google provider. Support login, logout, and token refresh.",
    "labels": [
      {"name": "generate-tests"}
    ],
    "html_url": "https://github.com/vtanathip/test-case-generator/issues/123",
    "user": {
      "login": "vtanathip"
    }
  },
  "repository": {
    "full_name": "vtanathip/test-case-generator"
  }
}
```

Send webhook request:

```powershell
# Calculate signature (simplified for testing)
$body = Get-Content test-webhook.json -Raw
$secret = "hjOb7Kg0BL5pDnl1FSv2Tqzf4QRHY6JU"
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::ASCII.GetBytes($secret)
$signature = "sha256=" + [BitConverter]::ToString($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body))).Replace("-","").ToLower()

# Send request
Invoke-WebRequest -Uri http://localhost:8000/webhooks/github `
  -Method POST `
  -Body $body `
  -ContentType "application/json" `
  -Headers @{
    "X-GitHub-Event" = "issues"
    "X-Hub-Signature-256" = $signature
    "X-GitHub-Delivery" = "12345678-1234-1234-1234-123456789012"
  }
```

Expected response: **202 Accepted** with correlation_id

### Test 2: Check Processing Status

```powershell
# View backend logs to see AI processing
docker-compose logs -f backend

# Check for:
# - "webhook_received" 
# - "processing_started"
# - "ai_generation_started"
# - "branch_created"
# - "pr_created"
```

### Test 3: Verify PR Creation

After 1-2 minutes, check your GitHub repository:
- New branch should exist: `test-cases/issue-123`
- New PR should be created linking to issue #123
- PR should contain Markdown test cases

---

## 🌐 Setting Up GitHub Webhooks (Optional)

To receive real GitHub events, you need a public URL.

### Option A: Cloudflare Tunnel (Free, Recommended)

1. Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
2. Run tunnel:
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
3. Note the URL (e.g., `https://abc-123.trycloudflare.com`)

### Option B: ngrok (Alternative)

1. Install ngrok: https://ngrok.com/download
2. Run tunnel:
   ```powershell
   ngrok http 8000
   ```
3. Note the URL (e.g., `https://1234-567-89.ngrok-free.app`)

### Configure GitHub Webhook

1. Go to: https://github.com/vtanathip/test-case-generator/settings/hooks
2. Click "Add webhook"
3. **Payload URL**: `https://YOUR-TUNNEL-URL/webhooks/github`
4. **Content type**: `application/json`
5. **Secret**: `hjOb7Kg0BL5pDnl1FSv2Tqzf4QRHY6JU` (from .env)
6. **Events**: Select "Issues" only
7. Click "Add webhook"

### Test Real Webhook

1. Create a new issue in your repository
2. Add label: `generate-tests`
3. Wait 1-2 minutes
4. Check for new PR with test cases!

---

## 🎯 What the MVP Does

When you create a GitHub issue with the `generate-tests` label:

1. **Webhook Received** → Backend validates signature
2. **Job Queued** → Creates ProcessingJob (status: PENDING)
3. **AI Processing** → LangGraph workflow runs (6 stages):
   - RECEIVE: Parse issue content
   - RETRIEVE: Query vector DB for similar tests (Phase 4, optional)
   - GENERATE: Llama 3.2 generates test cases
   - COMMIT: Create branch and commit Markdown file
   - CREATE_PR: Open pull request
   - FINALIZE: Add comment to issue
4. **PR Created** → Test cases ready for review!

---

## 📊 Monitoring

### View Logs
```powershell
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Ollama (LLM) only
docker-compose logs -f ollama
```

### Check Service Status
```powershell
docker-compose ps
```

### Access Dashboard
Open browser: http://localhost:3000

Shows:
- Processing statistics
- Recent issues
- Generated test cases
- System health

### API Documentation
Open browser: http://localhost:8000/docs

Interactive Swagger UI for all endpoints.

---

## 🐛 Troubleshooting

### Issue: "401 Unauthorized" when creating PR

**Cause**: Invalid GitHub token

**Fix**: 
1. Verify token has `repo` and `admin:repo_hook` scopes
2. Update `GITHUB_TOKEN` in `.env`
3. Restart: `docker-compose restart backend`

### Issue: Backend logs show "GITHUB_TOKEN not set"

**Cause**: Environment variable not loaded

**Fix**:
1. Verify `.env` file exists with correct values
2. Restart all services: `docker-compose down && docker-compose up -d`

### Issue: Slow AI generation (>5 minutes)

**Cause**: Running on CPU without GPU

**Options**:
1. Use smaller model: Change `LLAMA_MODEL=llama3.2:3b` in `.env`
2. Pull smaller model: `docker-compose exec ollama ollama pull llama3.2:3b`
3. Restart backend: `docker-compose restart backend`

### Issue: "Connection refused" to ChromaDB or Redis

**Cause**: Services not fully started

**Fix**: Wait 30 seconds after `docker-compose up`, then check:
```powershell
docker-compose ps
```
All services should show "healthy" or "running"

---

## 🎉 Next Steps

Once the MVP is working:

1. **Phase 4**: Add vector database context retrieval for better test cases
2. **Phase 5**: Add security hardening (rate limiting, enhanced validation)
3. **Phase 6**: Enhance dashboard UI with real-time updates
4. **Phase 7**: Production deployment with CI/CD

---

## 📚 Additional Resources

- **Developer Guide**: `docs/DEVELOPER_GUIDE.md`
- **Architecture**: `docs/langgraph-implementation.md`
- **Full Spec**: `specs/001-ai-test-generation/spec.md`
- **API Docs**: http://localhost:8000/docs

---

**Need Help?** Check logs first: `docker-compose logs -f backend`
