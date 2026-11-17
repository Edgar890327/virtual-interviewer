# Implementation Guide - New Features

## Overview

You have requested 7 major features that require significant changes to the application. This guide explains:

1. What has been completed
2. What needs to be done
3. Step-by-step implementation instructions
4. Timeline and effort estimates

---

## Completed Work ✅

### Backend Infrastructure (NEW FILES CREATED)

| File | Purpose | Status |
|------|---------|--------|
| `app/database.py` | SQLite user & interview storage | ✅ Ready |
| `app/auth.py` | User authentication & JWT tokens | ✅ Ready |
| `app/models_manager.py` | AI model detection & management | ✅ Ready |

### Enhanced Modules

| File | Changes | Status |
|------|---------|--------|
| `app/config.py` | Added JWT & database config | ✅ Ready |
| `app/ai.py` | Position description + guaranteed feedback | ✅ Ready |
| `app/schemas.py` | New auth & models schemas | ✅ Ready |
| `requirements.txt` | Added bcrypt, JWT, pydantic[email] | ✅ Ready |

---

## Remaining Work ⏳

### Critical - Must Do

**1. Update `app/main.py` (2-3 hours)**
   - Initialize SQLite database at startup
   - Add JWT authentication middleware
   - Remove Basic Auth dependency
   - Implement 12+ new endpoints
   - Update existing endpoints for user isolation

**2. Update Frontend (2-3 hours)**
   - Add user registration screen
   - Add user login screen with JWT
   - Add position description textarea
   - Add model selector dropdown
   - Add model availability alerts
   - Update interview flow to pass new data

---

## Implementation Checklist

### ✅ DONE - Infrastructure
- [x] Database schema designed
- [x] User CRUD operations implemented
- [x] Interview CRUD with user isolation
- [x] Password hashing (bcrypt)
- [x] JWT token generation/validation
- [x] Model manager with listing/pulling
- [x] Enhanced AI prompts
- [x] Fallback feedback generator
- [x] API schemas updated
- [x] Configuration updated
- [x] Dependencies added

### ⏳ TODO - Main Application

**Priority 1 (CRITICAL)**
- [ ] Update `app/main.py`:
  - [ ] Import new modules
  - [ ] Initialize database
  - [ ] Add JWT middleware
  - [ ] Add `/api/auth/register` endpoint
  - [ ] Add `/api/auth/login` endpoint
  - [ ] Add `/api/auth/me` endpoint
  - [ ] Add `/api/models` endpoint
  - [ ] Add `/api/models/download` endpoint
  - [ ] Update `/api/interviews/start` for users
  - [ ] Update `/api/interviews/{id}/turn` for users
  - [ ] Update `/api/interviews/{id}/finish` for guaranteed feedback
  - [ ] Update `/api/sessions` for user isolation
  - [ ] Update `/api/sessions/{id}/*` for user isolation
  - [ ] Remove hardcoded Basic Auth checks

**Priority 2 (IMPORTANT)**
- [ ] Update Frontend `static/index.html`:
  - [ ] Add registration screen
  - [ ] Add login screen
  - [ ] Add interview form fields:
    - [ ] Position description textarea
    - [ ] Model selector dropdown
  - [ ] Add model alert display
  - [ ] Update navigation for user profile

- [ ] Update `static/app.js`:
  - [ ] Add registration logic
  - [ ] Add login logic
  - [ ] Add JWT token storage/retrieval
  - [ ] Add token to all API calls
  - [ ] Add model selector logic
  - [ ] Add model availability check
  - [ ] Add model download UI

**Priority 3 (NICE TO HAVE)**
- [ ] Add user profile page
- [ ] Add model download progress indicator
- [ ] Add feedback preview on session list
- [ ] Add export with user info

---

## Step-by-Step Main.py Update

### Step 1: Add Imports and Initialization
```python
from app.database import init_db, UserDB, InterviewDB
from app.auth import authenticate_user, register_user, decode_token, create_access_token
from app.models_manager import ModelsManager
from app.schemas import (
    UserRegister, UserLogin, AuthResponse, UserInfo,
    ... # existing imports
)

# At app startup
@app.on_event("startup")
async def startup_event():
    init_db()
    # Initialize models manager
    app.state.models_manager = ModelsManager()
```

### Step 2: Add JWT Middleware
```python
async def get_current_user(token: str = Depends(HTTPBearer())) -> str:
    user_id = decode_token(token.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

# In endpoints:
@app.get("/api/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    user = UserDB.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInfo(**user)
```

### Step 3: Add Auth Endpoints
```python
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(data: UserRegister):
    user_id = register_user(data.username, data.email, data.password)
    if not user_id:
        raise HTTPException(status_code=400, detail="User already exists")
    token = create_access_token(user_id)
    return AuthResponse(access_token=token, user_id=user_id)

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(data: UserLogin):
    token = authenticate_user(data.username, data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = UserDB.get_user_by_username(data.username)
    return AuthResponse(access_token=token, user_id=user["id"])
```

### Step 4: Add Models Endpoints
```python
@app.get("/api/models")
async def list_models():
    models = await ModelsManager.list_models()
    return ModelsListResponse(
        models=models,
        available=len(models) > 0
    )

@app.post("/api/models/download")
async def download_model(model_name: str):
    success = await ModelsManager.pull_model(model_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to download model")
    return {"status": "success", "model": model_name}
```

### Step 5: Update Interview Endpoints

Replace the session-based endpoints with database-based, user-isolated versions.

---

## Frontend Implementation

### New HTML Elements Needed

```html
<!-- Registration Screen -->
<section id="register-screen" class="card">
  <h1>Create Account</h1>
  <input id="register-username" type="text" placeholder="Username">
  <input id="register-email" type="email" placeholder="Email">
  <input id="register-password" type="password" placeholder="Password">
  <button id="register-btn">Sign Up</button>
  <p><a href="#" onclick="switchToLogin()">Already have account? Login</a></p>
</section>

<!-- Enhanced Interview Form -->
<textarea id="position-description" placeholder="Position requirements and description (optional)" rows="6"></textarea>

<!-- Model Selector -->
<select id="model-select">
  <option value="">Loading models...</option>
</select>

<!-- Model Alert -->
<div id="model-alert" class="alert hidden">
  ⚠️ No AI models available. 
  <button onclick="downloadModel()">Download Model</button>
</div>
```

### JavaScript Logic Needed

```javascript
// JWT Token Management
const API_TOKEN_KEY = 'api_token';
const USER_ID_KEY = 'user_id';

function setToken(token, userId) {
  localStorage.setItem(API_TOKEN_KEY, token);
  localStorage.setItem(USER_ID_KEY, userId);
}

function getToken() {
  return localStorage.getItem(API_TOKEN_KEY);
}

function clearToken() {
  localStorage.removeItem(API_TOKEN_KEY);
  localStorage.removeItem(USER_ID_KEY);
}

// Helper to add token to requests
async function apiFetch(url, options = {}) {
  const token = getToken();
  if (token) {
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };
  }
  return fetch(url, options);
}

// Registration
async function register(username, email, password) {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, email, password})
  });
  
  if (res.ok) {
    const data = await res.json();
    setToken(data.access_token, data.user_id);
    showInterviewForm();
  }
}

// Login  
async function login(username, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, password})
  });
  
  if (res.ok) {
    const data = await res.json();
    setToken(data.access_token, data.user_id);
    showInterviewForm();
  }
}

// Model management
async function loadModels() {
  const res = await apiFetch('/api/models');
  if (res.ok) {
    const data = await res.json();
    populateModelSelector(data.models);
    if (!data.available) {
      showModelAlert();
    }
  }
}

async function downloadModel(modelName) {
  const res = await apiFetch('/api/models/download', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({model_name: modelName})
  });
  if (res.ok) {
    hideModelAlert();
    loadModels();
  }
}
```

---

## Testing Strategy

### Unit Tests
```bash
# Test database operations
pytest app/test_database.py

# Test auth functions
pytest app/test_auth.py

# Test models manager
pytest app/test_models.py
```

### Integration Tests
```bash
# Test full flow
python3 test_api.py
```

### Manual Tests
1. Register new user
2. Login and receive token
3. Create interview with position description
4. Check available models
5. Complete interview and verify feedback
6. Export session

---

## Database Initialization

The database is automatically initialized when app starts:

```python
@app.on_event("startup")
async def startup():
    init_db()  # Creates tables if they don't exist
```

---

## Migration Strategy

### Current System → New System

**Old Way:**
- Basic Auth with hardcoded credentials
- Sessions stored as JSON files
- No user accounts
- Single model per session

**New Way:**
- JWT tokens with user accounts
- Interviews stored in SQLite with user_id
- Multiple users, isolated data
- User can switch models per session

**Backward Compatibility:**
- Old JSON sessions still readable
- Can migrate to DB if needed
- Basic Auth still works as fallback (optional)

---

## Performance Considerations

### Database
- Interviews table indexed on user_id
- Queries include WHERE user_id = ? for isolation
- JSON storage in TEXT field (searchable)

### Model Switching
- Stored in session state
- Each user can use different model
- No performance impact on other users

### Feedback Generation
- Guaranteed with fallback
- Async operations for model pulling
- Timeout handling for failed requests

---

## Security Checklist

- [x] Passwords hashed with bcrypt
- [x] JWT tokens with expiration
- [x] User isolation in queries
- [x] Email validation
- [ ] HTTPS in production (TODO)
- [ ] Rate limiting on auth (TODO)
- [ ] CORS configuration (TODO)
- [ ] SQL injection prevention (using parameterized queries)

---

## Deployment Changes

### Docker
- No changes to Dockerfile needed
- Database mounts to volume: `interviews_db:/app/data`
- Environment variables:
  - JWT_SECRET_KEY (required in production)
  - DATABASE_PATH (optional)

### Environment
```bash
# Production .env
JWT_SECRET_KEY=<generate-strong-key>
OLLAMA_MODEL=llama3.1:8b
WHISPER_MODEL_SIZE=small
DATABASE_PATH=data/interview.db
```

---

## Timeline

| Phase | Task | Est. Time | Difficulty |
|-------|------|-----------|------------|
| 1 | Update app/main.py | 2-3h | Medium |
| 2 | Update frontend | 2-3h | Medium |
| 3 | Testing | 1-2h | Low |
| 4 | Documentation | 1h | Low |
| **Total** | | **6-9h** | **Medium** |

---

## Rollback Plan

If something breaks:

1. Keep backup of original `app/main.py`
2. Old code still in git history
3. Database schema backward compatible
4. JSON session files still exist

To rollback:
```bash
git checkout HEAD~1 app/main.py
docker compose down
docker compose up -d
```

---

## Questions & Support

1. Need help understanding database schema? → See `app/database.py`
2. Need auth examples? → See `app/auth.py`
3. Need model manager API? → See `app/models_manager.py`
4. Need endpoint examples? → See `IMPROVEMENTS_IN_PROGRESS.md`

---

**Next Step: Begin with `app/main.py` update (Phase 1)**

Start by copying the current version as backup, then implement new endpoints one at a time.

