# 📑 Interview App - Complete File Index

## 🎯 Quick Navigation

### 👤 For First-Time Users
1. **[START_HERE.md](./START_HERE.md)** - Begin here! (5 min read)
2. **[README.md](./README.md)** - Project overview (2 min read)
3. Run: `docker compose --profile init run --rm ollama-init`
4. Test: `python3 test_api.py`
5. Visit: http://127.0.0.1:8000

### 🏗️ For Developers/Architects
1. **[AGENT_HANDOFF.md](./AGENT_HANDOFF.md)** - Full architecture (10 min read)
2. **[PROJECT_STATUS.md](./PROJECT_STATUS.md)** - Detailed status (15 min read)
3. **[SESSION_5_SUMMARY.md](./SESSION_5_SUMMARY.md)** - Recent fixes (10 min read)
4. Code: `app/main.py` - API endpoints
5. Code: `app/ai.py` - LLM & STT integration

### 🧪 For QA/Testing
1. **[TESTING.md](./TESTING.md)** - Test procedures (5 min read)
2. Run: `python3 test_api.py`
3. Run: `./verify_setup.sh`
4. Manual testing in browser

### 🚀 For DevOps/Deployment
1. **[docker-compose.yml](./docker-compose.yml)** - CPU deployment
2. **[docker-compose.gpu.yml](./docker-compose.gpu.yml)** - GPU deployment
3. **[Dockerfile](./Dockerfile)** - App image
4. **[Dockerfile.ollama](./Dockerfile.ollama)** - Custom Ollama image
5. **[.env.example](./.env.example)** - Configuration template

---

## 📁 Complete File Listing

### 📖 Documentation (6 files)
```
INDEX.md                  ← This file (navigation guide)
START_HERE.md             ← User-friendly getting started guide
README.md                 ← Project overview & quick start
AGENT_HANDOFF.md          ← Technical architecture & API reference
TESTING.md                ← Testing & validation procedures
PROJECT_STATUS.md         ← Comprehensive status report
SESSION_5_SUMMARY.md      ← What was accomplished in session 5
```

### 🐍 Backend (6 files)
```
app/main.py               ← FastAPI application & all endpoints
app/ai.py                 ← Ollama LLM & Whisper STT clients
app/storage.py            ← Session persistence (JSON)
app/schemas.py            ← Pydantic data models
app/config.py             ← Configuration management
app/__init__.py           ← Package init
```

### 🎨 Frontend (3 files)
```
static/index.html         ← HTML structure
static/app.js             ← JavaScript logic
static/styles.css         ← CSS styling
```

### 🐳 Docker (7 files)
```
Dockerfile                ← Production image (CPU)
Dockerfile.gpu            ← Production image (GPU with NVIDIA)
Dockerfile.ollama         ← Custom Ollama image with CA certs
docker-compose.yml        ← CPU deployment configuration
docker-compose.gpu.yml    ← GPU deployment override
.env.example              ← Configuration template
.dockerignore             ← Docker build exclusions
```

### 🧪 Testing (2 files)
```
test_api.py               ← Automated test suite (7 tests)
verify_setup.sh           ← Quick verification script
```

### 📦 Dependencies (2 files)
```
requirements.txt          ← Python package requirements
.dockerignore             ← Files excluded from Docker builds
```

### 💾 Runtime (created at startup)
```
data/sessions/            ← Interview session storage
  ├── {uuid}.json        ← Individual session records
  └── ...
```

---

## 🚀 Common Tasks

### Setup & Start
```bash
cd /Users/edgargutierrez/src/interview
cp .env.example .env                              # Configure
docker compose up -d --build                      # Start containers
docker compose --profile init run --rm ollama-init # Download model
python3 test_api.py                               # Run tests
# Open http://127.0.0.1:8000
```

### Development
```bash
# Watch for Python changes
docker compose build app && docker compose up -d

# View logs
docker compose logs -f app

# Access shell in container
docker exec -it interview-app bash

# Stop everything
docker compose down
```

### Testing
```bash
# Run test suite
python3 test_api.py

# Verify setup
./verify_setup.sh

# Check specific endpoint
curl -u interviewer:super-segura http://127.0.0.1:8000/api/auth/login

# View container status
docker compose ps

# Check logs
docker compose logs app ollama
```

### Deployment
```bash
# CPU (default)
docker compose -f docker-compose.yml up -d --build

# GPU (NVIDIA Linux)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

# Production build
docker build -t interview-app:1.0 .
docker tag interview-app:1.0 myregistry.com/interview-app:1.0
docker push myregistry.com/interview-app:1.0
```

---

## 📊 File Size Reference

| File | Type | Size | Purpose |
|------|------|------|---------|
| AGENT_HANDOFF.md | Doc | 9.0KB | Architecture reference |
| PROJECT_STATUS.md | Doc | 10.5KB | Complete status |
| START_HERE.md | Doc | 6.8KB | Getting started |
| app/main.py | Python | 9.6KB | API endpoints |
| docker-compose.yml | YAML | 2.0KB | Container orchestration |
| Dockerfile | Text | 404B | Image definition |
| test_api.py | Python | 4.7KB | Test suite |

---

## 🔄 Workflow Examples

### For Beginners
1. Read START_HERE.md (5 min)
2. Follow "Next Steps" in START_HERE.md
3. Open http://127.0.0.1:8000
4. Login and try an interview
5. Check TESTING.md if issues occur

### For Backend Developers
1. Read AGENT_HANDOFF.md Section 3-6 (Architecture & API)
2. Review app/main.py (endpoints)
3. Review app/ai.py (LLM & STT integration)
4. Make changes to app/*.py
5. Rebuild: `docker compose build app`
6. Test: `docker compose up -d && python3 test_api.py`

### For Full-Stack Developers
1. Start with AGENT_HANDOFF.md (complete architecture)
2. Review app/ folder (backend logic)
3. Review static/ folder (frontend)
4. Make changes
5. For Python: rebuild with `docker compose build app`
6. For JS/CSS: reload browser (auto-picked up)
7. Test changes with test_api.py

### For DevOps/Infrastructure
1. Read README.md (deployment overview)
2. Review docker-compose.yml (CPU setup)
3. Review docker-compose.gpu.yml (GPU setup)
4. Review Dockerfile files
5. Review .env.example (configuration)
6. Adjust for your environment
7. Deploy using docker compose

### For Testers/QA
1. Read TESTING.md (comprehensive guide)
2. Read PROJECT_STATUS.md (known issues)
3. Run test_api.py (automated tests)
4. Run manual tests in browser
5. Check AGENT_HANDOFF.md Section 11 (troubleshooting)
6. Report issues with reproduction steps

---

## 🆘 Troubleshooting Guide

| Issue | Solution | Docs |
|-------|----------|------|
| Model won't download | See SSL certificate fix | START_HERE.md |
| API not responding | Check logs | TESTING.md |
| Tests failing | Run verify_setup.sh | TESTING.md |
| Container won't start | Check docker logs | TESTING.md |
| Port 8000 in use | Change port in compose | TESTING.md |
| Authentication failed | Check .env credentials | AGENT_HANDOFF.md |

---

## 📞 Support Resources

- **Getting Started**: START_HERE.md
- **Quick Setup**: README.md
- **Technical Details**: AGENT_HANDOFF.md
- **Testing**: TESTING.md
- **Status**: PROJECT_STATUS.md
- **Recent Work**: SESSION_5_SUMMARY.md
- **This Index**: INDEX.md

---

## ✅ Verification Checklist

Use this to verify everything is working:

- [ ] Docker containers running: `docker compose ps`
- [ ] App endpoint responds: `curl http://127.0.0.1:8000/api/auth/login`
- [ ] Tests pass: `python3 test_api.py`
- [ ] Browser loads: http://127.0.0.1:8000
- [ ] Login works: interviewer / super-segura
- [ ] Model status: `docker exec interview-ollama ollama list`

---

## 🎯 Next Steps

1. **If you're new**: Read START_HERE.md (5 min)
2. **If you're technical**: Read AGENT_HANDOFF.md (10 min)
3. **If you want to test**: Read TESTING.md (5 min)
4. **If you want status**: Read PROJECT_STATUS.md (15 min)

---

*Generated: August 19, 2024 (Session 5)*  
*Status: Application ready for use, model download pending*
