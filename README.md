# AI Interview App — Voz + Modelo Local

Aplicación web para practicar entrevistas con:

- **Registro y login de usuarios** (JWT, bcrypt) — historial por usuario.
- Captura de datos del entrevistado, posición e **descripción completa del puesto**.
- Selección de idioma (`es` / `en`), duración y modelo IA.
- Entrevista conversacional por **voz** (Whisper local).
- Preguntas dinámicas generadas por un modelo local (Ollama).
- **Alerta y descarga** si no hay modelos disponibles en Ollama.
- Feedback estructurado **garantizado** (Fortalezas / Mejoras / Score / Recomendación).
- Historial persistente por usuario en **PostgreSQL**.
- Exportación de sesiones en JSON y PDF.

---

## 1) Requisitos

- Docker ≥ 24 y Docker Compose v2
- Micrófono disponible en el navegador

> Para desarrollo sin Docker: Python 3.11+, PostgreSQL 15+, FFmpeg, Ollama.

---

## 2) Levantar con Docker Compose (recomendado)

```bash
# 1. Copia y ajusta variables de entorno
cp .env.example .env
# Edita .env: POSTGRES_PASSWORD, JWT_SECRET_KEY, OLLAMA_MODEL

# 2. Construye e inicia todos los servicios
docker compose up -d --build

# 3. (Primera vez) descarga el modelo en Ollama
docker compose --profile init run --rm ollama-init

# 4. Abre la app
open http://localhost:8000
```

Servicios levantados:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `postgres` | 5432 | Base de datos PostgreSQL |
| `ollama` | 11434 | Servidor de modelos LLM |
| `app` | 8000 | FastAPI + frontend |

Datos persistentes en volúmenes Docker:

- `postgres_data` — usuarios e historial de entrevistas
- `ollama_data` — modelos descargados
- `sessions_data` — archivos JSON de sesiones (legado)

Para detener:

```bash
docker compose down          # mantiene volúmenes
docker compose down -v       # borra datos
```

---

## 3) Variables de entorno

Ver [.env.example](.env.example) para la lista completa.

| Variable | Default | Descripción |
|----------|---------|-------------|
| `POSTGRES_DB` | `interviewdb` | Nombre de la base de datos |
| `POSTGRES_USER` | `interview` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | `interview_secret` | **Cambiar en producción** |
| `DATABASE_URL` | auto-construida | URL completa de conexión |
| `JWT_SECRET_KEY` | `change-this-secret` | **Cambiar en producción** |
| `OLLAMA_MODEL` | `llama3.1:8b` | Modelo LLM a usar |
| `OLLAMA_API_KEY` | — | Clave de API de Ollama Cloud, si aplica |
| `WHISPER_MODEL_SIZE` | `small` | Tamaño del modelo Whisper |

---

## 4) Flujo de usuario

1. **Registro** → crea cuenta con usuario, email y contraseña.
2. **Login** → autenticación con JWT (30 días).
3. **Configurar entrevista** → nombre, email, posición, descripción del puesto, idioma, duración, modelo IA.
4. **Entrevista por voz** → el agente pregunta, el candidato responde por micrófono o texto.
5. **Feedback** → al terminar, el modelo genera feedback estructurado (siempre garantizado).
6. **Historial** → solo visible para el usuario autenticado; exportable en JSON/PDF.

---

## 5) Desarrollo sin Docker

```bash
# 1. Instala dependencias del sistema
brew install ffmpeg ollama
ollama pull llama3.1:8b

# 2. Crea y activa entorno Python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Levanta PostgreSQL local (o usa DATABASE_URL apuntando a tu instancia)
# Ejemplo con brew:
brew services start postgresql@16
createdb interviewdb
createuser interview
psql -c "ALTER USER interview PASSWORD 'interview_secret';"
psql -c "GRANT ALL ON DATABASE interviewdb TO interview;"

# 4. Configura variables
export DATABASE_URL=postgresql://interview:interview_secret@localhost:5432/interviewdb
export JWT_SECRET_KEY=dev-secret-key

# 5. Corre la app
uvicorn app.main:app --reload
```

---

## 6) Opción GPU (NVIDIA + Docker)

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

> macOS con Docker Desktop no soporta GPU passthrough NVIDIA.

---

## 7) Endpoints principales

Todos los endpoints de entrevistas requieren header `Authorization: Bearer <token>`.

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/register` | Registro de usuario |
| POST | `/api/auth/login` | Login → retorna JWT |
| GET | `/api/auth/me` | Info del usuario actual |
| GET | `/api/models` | Lista modelos en Ollama |
| POST | `/api/models/download` | Descarga un modelo |
| POST | `/api/interviews/start` | Inicia entrevista |
| POST | `/api/interviews/{id}/turn` | Turno de conversación |
| POST | `/api/interviews/{id}/finish` | Termina + genera feedback |
| GET | `/api/interviews` | Historial del usuario |
| GET | `/api/sessions/{id}/export/json` | Exportar JSON |
| GET | `/api/sessions/{id}/export/pdf` | Exportar PDF |

---

## 8) Handoff técnico

Para contexto técnico completo (arquitectura, base de datos, flujos, riesgos), ver:

- [AGENT_HANDOFF.md](AGENT_HANDOFF.md)
