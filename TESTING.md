# Testing & Validation Guide

## Quick Test Suite

### Prerequisites
- Docker running with app and ollama containers up: `docker compose up -d`
- Python 3.8+ with `requests` installed locally: `pip install requests`

### Run All Tests
```bash
cd /path/to/interview
python3 test_api.py
```

**Expected output**:
```
============================================================
API Test Suite - Interview App
============================================================

[TEST] Static Files
  Status: 200
  ✓ Frontend served correctly

[TEST] Auth Login
  Status: 200
  Response: {'ok': True}
  ✓ Auth works

[TEST] List Sessions
  Status: 200
  ✓ Sessions endpoint works

[TEST] Start Interview
  Status: 502 (model not ready) or 200 (if model is ready)
  ...
```

## What's Working

✅ **Infrastructure**
- Docker Compose CPU/GPU deployments
- Container healthchecks
- Volume persistence for sessions

✅ **API Layer**
- Basic Auth protection on all `/api/*` endpoints
- Session CRUD operations
- Interview lifecycle (create → turn → finish)
- JSON/PDF export

✅ **Frontend**
- HTML/CSS/JS served correctly
- Login screen renders
- Responsive design

✅ **Persistence**
- Session files stored in `data/sessions/{uuid}.json`
- Sessions queryable via `/api/sessions`
- Export functionality (JSON/PDF)

## What Needs Ollama Model

❌ **Interview Generation** (requires Ollama model)
- Starting an interview fails with `"Local LLM error while generating first question"`
  because the model is not downloaded

**Fix**: Download the Ollama model (see [AGENT_HANDOFF.md - Section 11](./AGENT_HANDOFF.md#11-known-issues--troubleshooting))

```bash
# Option 1: Using profile
docker compose --profile init run --rm ollama-init

# Option 2: Manual download
docker exec interview-ollama ollama pull llama3.1:8b

# Option 3: Check if model exists
docker exec interview-ollama ollama list
```

Once model is downloaded, run `test_api.py` again — `[TEST] Start Interview` should show `Status: 200`.

## Manual Testing

### 1. UI Test (Browser)
```
1. Open http://127.0.0.1:8000
2. Login: username=interviewer, password=super-segura
3. Click "New Interview"
4. Fill form:
   - Candidate Name: John Doe
   - Email: john@example.com
   - Position: Backend Engineer
   - Language: English
   - Duration: 5 minutes
5. Click "Start"
6. (Will fail if model not ready, but shows interview UI)
```

### 2. API Test (cURL)

**Auth**:
```bash
AUTH=$(echo -n "interviewer:super-segura" | base64)
curl -s http://127.0.0.1:8000/api/auth/login \
  -H "Authorization: Basic $AUTH"
```

**List Sessions**:
```bash
AUTH=$(echo -n "interviewer:super-segura" | base64)
curl -s http://127.0.0.1:8000/api/sessions \
  -H "Authorization: Basic $AUTH" | jq .
```

**Export Session (JSON)**:
```bash
AUTH=$(echo -n "interviewer:super-segura" | base64)
SESSION_ID="<copy-from-list-sessions>"
curl -s http://127.0.0.1:8000/api/sessions/$SESSION_ID/export/json \
  -H "Authorization: Basic $AUTH" > session.json
```

### 3. Docker Health Check
```bash
docker compose ps

# Expected output:
# NAME               STATUS
# interview-app      Up ... (healthy)
# interview-ollama   Up ... (healthy)
```

### 4. Logs
```bash
# App logs
docker compose logs app

# Ollama logs
docker compose logs ollama

# Follow logs in real-time
docker compose logs -f
```

## Deployment Validation

### CPU Mode (Default)
```bash
# Build & start
docker compose up -d --build

# Wait 30s for startup
sleep 30

# Verify health
docker compose ps

# Check app responds
curl -s http://127.0.0.1:8000/ | grep -q "AI Interview App" && echo "✓ App OK"
```

### GPU Mode (NVIDIA Linux)
```bash
# Build & start with GPU override
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

# Wait 30s
sleep 30

# Verify GPU is detected (optional, requires nvidia-docker or nvidia-container-toolkit)
docker compose logs app | grep -i cuda || docker compose logs app | grep -i gpu
```

## Troubleshooting

### App container crashes on startup
- Check logs: `docker compose logs app`
- Common causes:
  - Missing dependencies: validate `requirements.txt`
  - Port 8000 already in use: `lsof -i :8000`
  - Permission issues on volumes: check `data/sessions/` directory ownership

### Ollama container unhealthy
- Check logs: `docker compose logs ollama`
- Common causes:
  - SSL certificate issue (see AGENT_HANDOFF.md section 11)
  - Ollama not responding on port 11434
  - Model pull timeout (first pull can take 10+ minutes)

### API returns 502
- Likely cause: Ollama service not healthy
- Check: `docker compose ps ollama` → should show `healthy`
- If not healthy, wait 30s and try again

### Login fails
- Verify credentials in `.env` file match `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD`
- Default credentials: `interviewer` / `super-segura`
- Header must be: `Authorization: Basic <base64(username:password)>`

## CI/CD Integration

For automated testing:

```bash
#!/bin/bash
set -e

# Build
docker compose build

# Start
docker compose up -d --build

# Wait for healthy
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if docker compose ps | grep -q "healthy"; then
    echo "✓ Services healthy"
    break
  fi
  echo "Waiting for services... ($((attempt+1))/$max_attempts)"
  sleep 10
  ((attempt++))
done

# Run tests
python3 test_api.py

# Cleanup
docker compose down
```

## Performance Testing (Optional)

Once model is ready, you can load-test the `/api/interviews/start` endpoint:

```bash
# Using Apache Bench (ab)
ab -n 10 -c 2 \
  -H "Authorization: Basic $(echo -n 'interviewer:super-segura' | base64)" \
  http://127.0.0.1:8000/api/interviews/start

# Using wrk (if available)
wrk -t2 -c2 -d10s \
  -H "Authorization: Basic $(echo -n 'interviewer:super-segura' | base64)" \
  http://127.0.0.1:8000/api/interviews/start
```

## Monitoring

Check container resource usage:
```bash
docker stats
```

Check volumes:
```bash
docker volume inspect interview_sessions_data
docker volume inspect interview_ollama_data
```

Check persisted sessions:
```bash
# Sessions are stored here
ls -lah data/sessions/

# Inspect a session file
cat data/sessions/<uuid>.json | jq .
```
