# CogniCompanion — Backend

> AI-Based Cognitive Gaming and Memory Assistance Platform for Elderly Dementia Patients in the North Eastern Region

---
.\venv312\Scripts\python.exe -m uvicorn app.main:app --port 8000 2>&1
## Quick Start
## Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 16+ with **pgvector** extension
- pip / venv

### 2. Setup

```bash
# Clone and enter the backend directory
cd cognicompanion/backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env
# Edit .env — fill in DATABASE_URL, SYNC_DATABASE_URL, JWT_SECRET, GOOGLE_API_KEY
```

### 3. Database Setup

```bash
# Create the PostgreSQL database
psql -U postgres -c "CREATE USER cogni_user WITH PASSWORD 'cogni_pass';"
psql -U postgres -c "CREATE DATABASE cognicompanion OWNER cogni_user;"
psql -U postgres -d cognicompanion -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
alembic upgrade head
```

### 4. Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
Health: [http://localhost:8000/health](http://localhost:8000/health)

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                    ← FastAPI app entrypoint
│   ├── core/
│   │   ├── config.py              ← Settings (Pydantic BaseSettings)
│   │   ├── database.py            ← Async SQLAlchemy engine
│   │   ├── security.py            ← JWT + bcrypt
│   │   ├── exceptions.py          ← Custom HTTP exceptions
│   │   └── storage.py             ← File storage abstraction
│   ├── domains/
│   │   ├── auth/                  ← Login, JWT, RBAC
│   │   ├── patients/              ← Users, Patients, CaregiverPatient
│   │   ├── memories/              ← People, Memories, Media
│   │   ├── timeline/              ← Medications, Routines, Events
│   │   ├── games/                 ← Games, GameSessions
│   │   ├── analytics/             ← DailyStats, CPI
│   │   └── voice/                 ← Conversations, Messages, Embeddings
│   ├── ai/
│   │   ├── providers/             ← LLM, STT, TTS, Embeddings (Gemini)
│   │   └── memory_engine/         ← PME components (Phase 4)
│   └── events/
│       ├── bus.py                 ← In-process event bus
│       └── handlers.py            ← Domain event handlers
├── migrations/
│   └── versions/
│       └── 0001_initial_schema.py ← Full schema + pgvector + game seeds
├── tests/
│   ├── conftest.py                ← Pytest fixtures
│   └── test_auth.py               ← Auth tests
├── .env.example                   ← Environment template
├── alembic.ini
└── requirements.txt
```

---

## API Endpoints (Phase 1)

| Method | Path | Description | Role |
|--------|------|-------------|------|
| POST | `/api/v1/auth/login` | Authenticate | Any |
| POST | `/api/v1/auth/refresh` | Refresh access token | Any |
| GET | `/api/v1/auth/me` | Current user info | Authenticated |
| POST | `/api/v1/patients/` | Create patient | CAREGIVER, ADMIN |
| GET | `/api/v1/patients/` | List my patients | CAREGIVER, ADMIN |
| GET | `/api/v1/patients/{id}` | Patient details | CAREGIVER (assigned), ADMIN |
| PATCH | `/api/v1/patients/{id}` | Update patient | CAREGIVER (assigned), ADMIN |
| POST | `/api/v1/patients/{id}/caregivers` | Assign caregiver | ADMIN |
| GET | `/health` | Health check | Public |

---

## Running Tests

```bash
pip install aiosqlite   # Needed for in-memory test DB
pytest tests/ -v
```

---

## CPI Formula

> **CPI is an assistive performance indicator — NOT a medical diagnosis.**

```
CPI = 40% × Memory Accuracy
    + 25% × Reaction Performance
    + 20% × Completion Rate
    + 15% × Engagement Score
```

Final CPI is displayed on a 0–100 scale.

---

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Project setup + structure | ✅ Done |
| 1 | DB schema + Auth + Patients | ✅ Done |
| 2 | Memory system + Timeline | ✅ Done |
| 3 | First vertical slice (ask → recall → answer) | ✅ Done |
| 4 | Personalized Memory Engine (PME) | ✅ Done |
| 5 | Voice Interaction Pipeline (STT/TTS) | ✅ Done |
| 6 | Cognitive Games & Personalization | ✅ Done |
| 7 | Adaptive difficulty engine | ✅ Done |
| 8 | Analytics + CPI | ✅ Done |
| 9 | Caregiver Dashboard | ✅ Done |
| 10 | Offline support | ✅ Done |
| 11 | Security hardening | ✅ Done |
| 12 | Testing | ✅ Done |
| 13 | Deployment | ✅ Done |
