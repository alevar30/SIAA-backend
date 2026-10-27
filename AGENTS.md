# AGENTS.md

SIAA (Sistema Institucional de Asesorías Académicas) — academic advising management system. FastAPI + PostgreSQL backend, React + Vite frontend. Docs and UI are written in Spanish.

i am an stundent, very time i ask you or you do something explain it to me and tell me why you decide that

## Current state — read before doing anything

This is an **early scaffold**, not a working app. Do not assume folders contain functionality:

- **Written and working**: `app/main.py` defines `app = FastAPI(...)` plus a `GET /health-db` diagnostic route (runs `SELECT 1` via `Depends(get_db)`) and mounts `app/api/v1/router.py`. `app/core/config.py` defines `Settings` (pydantic-settings; reads `.env`, exposes `ASYNC_DATABASE_URL`). `app/db/session.py` defines the async engine, `AsyncSessionLocal` and the `get_db()` dependency. `app/db/base.py` defines `Base` (`DeclarativeBase`), so **all models import correctly**. `app/models/user.py` (`Role`, `User`), `app/models/academic.py` (`Career`, `Subject`, `Topic`) and `app/models/profiles.py` (`Student`, `Teacher`) exist — **7 tables registered** in `Base.metadata`.
- Still **empty (0 bytes)**: `app/core/session.py`.
- **Alembic is now set up and runnable**: `alembic.ini` filled, `alembic/env.py` complete (sync `psycopg` driver, `psycopg[binary]` added to requirements and installed), and the first migration (`crear tablas iniciales`) is **applied** — the 7 domain tables exist in PostgreSQL. Missing tables from the guide (`disponibilidades`, `asesorias`, `participantes_asesoria`, M2M tables) are **not modeled yet**.
- `frontend/` **does not exist** — React + Vite has not been scaffolded.
- The repo **is** a git repository now, but has **no commits yet** and no `.gitignore` (`.env` is untracked but not ignored — keep secrets out of commits).

## Commands

Backend (Python 3.12; deps are already installed in `backend/.venv`):

```bash
cd backend
source .venv/bin/activate          # or call .venv/bin/python directly
uvicorn app.main:app --reload      # serves `app`; only /health-db exists so far
.venv/bin/pip install -r requirements.txt
```

- `pytest` is the intended test runner but **pytest/httpx are not installed** yet. Guide layout expects `backend/tests/{unit,integration}` + `conftest.py` (not created).
- Alembic (only after filling the empty `alembic.ini` and completing `alembic/env.py`):

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
alembic history
```

Frontend (only after scaffolding with `npm create vite@latest frontend -- --template react`):

```bash
npm install
npm run dev
npm run build
```

## Configuration / env quirks

- `backend/.env` exists with **local dev credentials** using `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_DB`, plus `SECRET_KEY`.
- The guide's examples use a single `DATABASE_URL` instead, but `app/core/config.py` already follows the `POSTGRES_*` form and builds `ASYNC_DATABASE_URL` from it, so follow that convention.
- No `.env.example` exists. Keep real secrets out of any `.env.example` you create.

## Intended architecture (from the guide's scaffold)

- API prefix `/api/v1`; routers should live in `app/api/v1/endpoints/` (not created yet), aggregated by the currently-empty `app/api/v1/router.py` and mounted from `main.py`.
- Layering: endpoints → Pydantic schemas → services → repositories → SQLAlchemy models. `services/` and `repositories/` are planned but not yet created.
- DB access is **async SQLAlchemy 2.0 + asyncpg**; auth is **JWT (python-jose) + passlib[bcrypt]**.
- Domain entities: `roles, usuarios, estudiantes, docentes, carreras, materias, temas, disponibilidades, asesorias, participantes_asesoria`. Individual and group advising sessions share the `asesorias` table (ADR-003).

## Documentation conflict — resolved

Two architecture docs exist at the root:

- `GUIA_SIAA_REACT_FASTAPI.md` — detailed, authoritative dev guide. ADR-001 explicitly decides **React + Vite**.
- `PROJECT_WORKFLOW.md` — architecture/workflow summary. It previously mentioned Flutter/React Native, but it has been **updated to React + Vite** to match ADR-001. If you see the old Flutter wording anywhere, treat it as outdated.
