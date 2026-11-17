# Agent Handoff — AI Interview App

> Documento para que un agente en nueva sesión tome el proyecto y trabaje rápido.
> Última actualización: agosto 2026 — migración a PostgreSQL + registro de usuarios.

---

## 1) Objetivo del producto

Aplicación web para entrevistas simuladas por voz con modelo local:

- Registro y login de usuarios (JWT, bcrypt)
- Captura de datos del candidato y vacante con **descripción completa del puesto**
- Selección de idioma (`es`/`en`), duración, y modelo IA
- Entrevista conversacional con preguntas dinámicas (Ollama)
- STT local (faster-whisper) para respuestas por audio
- Alerta + descarga si no hay modelos disponibles
- Feedback estructurado **garantizado** (con fallback si el LLM falla)
- Historial persistente **por usuario** en PostgreSQL
- Exportación de sesiones en JSON y PDF

---

## 2) Estado actual del proyecto

### Stack técnico

| Componente | Tecnología |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Frontend | HTML/CSS/JS vanilla |
| Base de datos | **PostgreSQL 16** (psycopg2-binary) |
| Sesiones en memoria | JSON files (storage.py — legado, se mantiene por PDF export) |
| LLM local | Ollama (`/api/chat`) |
| STT | faster-whisper |
| Autenticación | JWT (PyJWT) + bcrypt |
| PDF export | ReportLab |

### Archivos clave

| Archivo | Propósito |
|---|---|
| `app/main.py` | FastAPI app — todos los endpoints |
| `app/database.py` | CRUD PostgreSQL (UserDB, InterviewDB) |
| `app/auth.py` | Hash bcrypt, JWT encode/decode |
| `app/models_manager.py` | Lista y descarga modelos Ollama |
| `app/ai.py` | LocalLLMClient (preguntas + feedback) + SpeechToText |
| `app/schemas.py` | Pydantic models para request/response |
| `app/config.py` | Variables de entorno |
| `app/storage.py` | Sesiones JSON en disco (legado, aún usado para export) |
| `static/index.html` | UI — pantallas auth/setup/interview/feedback/history |
| `static/app.js` | Lógica frontend — JWT, registro, modelos, voz |
| `static/styles.css` | Dark theme + tabs de auth |
| `docker-compose.yml` | postgres + ollama + app |
| `requirements.txt` | Dependencias Python |
| `.env.example` | Variables de entorno de referencia |

---

## 3) Arquitectura lógica

```
Browser
  │
  ├─ GET /          → index.html (public)
  ├─ POST /api/auth/register → crea user en PostgreSQL, retorna JWT
  ├─ POST /api/auth/login    → valida bcrypt, retorna JWT
  │
  │  (todos siguientes requieren header: Authorization: Bearer <token>)
  │
  ├─ GET  /api/models                → lista modelos en Ollama
  ├─ POST /api/models/download       → pull modelo en Ollama
  ├─ POST /api/interviews/start      → crea sesión en PG + genera 1ª pregunta
  ├─ POST /api/interviews/{id}/turn  → transcribe audio → LLM → siguiente pregunta
  ├─ POST /api/interviews/{id}/finish→ genera feedback → guarda en PG
  ├─ GET  /api/interviews            → lista interviews del usuario (PG)
  └─ GET  /api/sessions/{id}/export/json|pdf
```

### Aislamiento por usuario

Todas las queries de InterviewDB incluyen `WHERE user_id = %s`. Un usuario nunca ve entrevistas de otro.

---

## 4) Base de datos (PostgreSQL)

### Schema

```sql
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE interviews (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    candidate_name       TEXT NOT NULL,
    candidate_email      TEXT,
    position             TEXT NOT NULL,
    position_description TEXT,
    language             TEXT NOT NULL,
    duration_minutes     INTEGER NOT NULL,
    started_at           TIMESTAMPTZ DEFAULT NOW(),
    finished_at          TIMESTAMPTZ,
    feedback             TEXT,
    messages             JSONB DEFAULT '[]'::jsonb,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_interviews_user ON interviews(user_id);
```

### Conexión

La app usa `psycopg2` síncrono con context manager `get_db()` en `app/database.py`. Cada operación abre y cierra conexión (sin pool — suficiente para MVP, reemplazar con `psycopg2.pool` o SQLAlchemy si escala).

### Inicialización

`init_db()` se llama en el evento `startup` de FastAPI. Crea tablas si no existen (idempotente).

---

## 5) Autenticación

- **Registro**: `POST /api/auth/register` → `UserDB.create_user()` → hash bcrypt → retorna JWT
- **Login**: `POST /api/auth/login` → `UserDB.get_user_by_username()` → `verify_password()` → retorna JWT
- **Token**: JWT firmado con `JWT_SECRET_KEY`, expira en 30 días
- **Middleware**: `get_current_user()` como `Depends` en cada endpoint protegido — extrae `user_id` del payload

Token se almacena en `localStorage` del navegador.

---

## 6) Arquitectura de despliegue

### Docker Compose (CPU)

```yaml
services:
  postgres:   # PostgreSQL 16, healthcheck pg_isready
  ollama:     # Servidor de modelos
  app:        # FastAPI, depende de postgres + ollama healthy
  ollama-init:# perfil 'init' — descarga modelo
```

Volúmenes: `postgres_data`, `ollama_data`, `sessions_data`

### Variables de entorno del contenedor `app`

```bash
DATABASE_URL=postgresql://interview:interview_secret@postgres:5432/interviewdb
JWT_SECRET_KEY=change-this-secret-in-production
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

### GPU override

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

---

## 7) Flujo frontend

### Pantallas

1. **Auth screen** — tabs Login / Crear cuenta
2. **Model alert** (banner) — si Ollama no tiene modelos, muestra selector + botón descargar
3. **Setup screen** — configuración de entrevista + selector de modelo
4. **Interview screen** — chat + grabación de voz + timer
5. **Feedback screen** — feedback renderizado como markdown
6. **History screen** — lista de entrevistas del usuario + detalle

### Tokens JWT en JS

```javascript
// Guardar
localStorage.setItem("jwt_token", data.access_token);
// Usar en fetch
headers.set("Authorization", `Bearer ${jwtToken}`);
// Al arrancar
if (jwtToken) afterLogin(); else show(authScreen);
```

---

## 8) Endpoints completos

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/` | ❌ | Sirve index.html |
| POST | `/api/auth/register` | ❌ | Registro → JWT |
| POST | `/api/auth/login` | ❌ | Login → JWT |
| GET | `/api/auth/me` | ✅ | Info usuario |
| GET | `/api/models` | ✅ | Lista modelos Ollama |
| POST | `/api/models/download?model_name=` | ✅ | Pull modelo |
| POST | `/api/models/select?model_name=` | ✅ | Seleccionar modelo |
| POST | `/api/interviews/start` | ✅ | Iniciar entrevista |
| POST | `/api/interviews/{id}/turn` | ✅ | Turno (audio o texto) |
| POST | `/api/interviews/{id}/finish` | ✅ | Terminar + feedback |
| GET | `/api/interviews` | ✅ | Historial del usuario |
| GET | `/api/interviews/{id}` | ✅ | Detalle entrevista |
| GET | `/api/sessions/{id}` | ✅ | Alias legacy |
| GET | `/api/sessions/{id}/export/json` | ✅ | Export JSON |
| GET | `/api/sessions/{id}/export/pdf` | ✅ | Export PDF |

---

## 9) Decisiones de diseño

- **psycopg2 síncrono**: FastAPI puede ser async pero los endpoints de entrevista no son I/O intensivo — sync es más simple y funciona bien.
- **JSONB para messages**: Permite queries sobre el transcript si se necesita análisis futuro.
- **storage.py legado**: Se mantiene en paralelo a PostgreSQL porque el export PDF lee el objeto `InterviewSession` que vive en disco. Refactorizar export para leer de PG sería el siguiente paso.
- **JWT en localStorage**: Simple para MVP; para producción considerar httpOnly cookies.
- **Feedback garantizado**: `llm.feedback()` tiene try/except → `_fallback_feedback()` — nunca falla.

---

## 10) Riesgos / limitaciones conocidas

| Issue | Impacto | Fix sugerido |
|---|---|---|
| Sin pool de conexiones PostgreSQL | Performance bajo carga alta | psycopg2.pool o SQLAlchemy |
| Sessions JSON en disco (storage.py) | Inconsistencia con PG | Refactorizar export a leer de PG |
| JWT en localStorage | XSS puede robar token | httpOnly cookie en producción |
| Sin rate limiting | Brute force login | Agregar slowapi o nginx rate limit |
| Whisper descarga modelo en primer uso | ~500MB primera vez | Pre-descargar en imagen Docker |
| SSL cert en Ollama registry | Pull puede fallar en redes corporativas | Ver sección 12 |

---

## 11) Runbook rápido para nuevo agente

```bash
# 1. Clonar y configurar
cp .env.example .env
# Editar .env: cambiar POSTGRES_PASSWORD y JWT_SECRET_KEY

# 2. Levantar servicios
docker compose up -d --build

# 3. Descargar modelo (primera vez)
docker compose --profile init run --rm ollama-init
# Si falla SSL: docker exec interview-ollama ollama pull llama3.1:8b

# 4. Verificar
curl http://localhost:8000/               # → HTML
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"t@t.com","password":"test1234"}'
# → {"access_token":"...","user_id":"..."}

# 5. Verificar PostgreSQL
docker exec interview-postgres psql -U interview -d interviewdb \
  -c "SELECT username, email FROM users;"
```

---

## 12) Troubleshooting

### SSL error en ollama pull

```
tls: failed to verify certificate: x509: certificate signed by unknown authority
```

**Fix**: `docker exec interview-ollama ollama pull llama3.1:8b` (usa certificados del host vía Docker socket).

### App no conecta a PostgreSQL

```
psycopg2.OperationalError: could not connect to server
```

**Fix**: Verificar que `postgres` está healthy: `docker compose ps`. La app espera healthcheck de PG antes de arrancar.

### Modelo no disponible → 502 en interviews/start

**Fix**: 
```bash
docker exec interview-ollama ollama list    # verificar modelos
docker exec interview-ollama ollama pull llama3.1:8b
```

### Frontend muestra error 401

**Fix**: Token expirado — cerrar sesión y volver a loguearse. Los tokens duran 30 días.

---

## 13) Backlog sugerido

1. **Refactorizar export** para leer de PostgreSQL (eliminar dependencia de storage.py)
2. **Pool de conexiones** con psycopg2.pool o SQLAlchemy + alembic para migraciones
3. **Streaming de respuestas** del LLM con SSE
4. **TTS local** con edge-tts o kokoro
5. **Scoring estructurado** por competencias (rubric JSON)
6. **Rate limiting** en login/register (slowapi)
7. **Refresh tokens** para renovar JWT sin re-login
8. **Dashboard analytics** — estadísticas de entrevistas por usuario
