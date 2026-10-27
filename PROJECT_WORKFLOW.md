# Documentación de Arquitectura y Flujo de Trabajo — SIAA

> Estado: scaffold temprano (Fase 1). Este documento se actualiza a medida
> que avanza el proyecto. La fuente autoritativa de decisiones es
> `GUIA_SIAA_REACT_FASTAPI.md`. El frontend es **React** (ADR-001); cualquier
> mención previa a Flutter/React Native queda descartada.

## 1. Stack tecnológico

| Capa            | Tecnología                          | Justificación                                          |
|-----------------|-------------------------------------|--------------------------------------------------------|
| Backend         | Python 3.12+ / FastAPI              | Rendimiento, asyncio nativo y Swagger automático       |
| Base de datos   | PostgreSQL                          | Integridad relacional para el dominio académico        |
| ORM             | SQLAlchemy 2.0 (async + asyncpg)    | Mapeo asíncrono con el estilo tipado moderno           |
| Migraciones     | Alembic                             | Versionado del esquema de BD                           |
| Auth            | JWT (python-jose) + passlib[bcrypt] | Sesiones stateless seguras                             |
| Frontend        | React + Vite                        | Decisión ADR-001; SPA que consume la API REST          |

## 2. Flujo de trabajo del sistema

```text
[ Cliente React (Vite) ]
           │  HTTP REST / JSON
           ▼
[ FastAPI / Uvicorn ]
   ├── Middleware (CORS, Auth JWT)
   ├── Endpoints (/api/v1/...)        ← app/api/v1/
   ├── Schemas Pydantic               ← validación entrada/salida
   └── Services → Repositories        ← lógica de negocio + acceso a datos
           │  SQLAlchemy 2.0 async
           ▼
[ PostgreSQL ]
```

Arquitectura por capas:

```text
endpoints → schemas → services → repositories → models → BD
```

### Ciclo de una petición

1. El cliente envía credenciales a `/api/v1/auth/login` y recibe un JWT.
2. Envía el header `Authorization: Bearer <TOKEN>` en cada petición.
3. FastAPI valida el token y el cuerpo con esquemas Pydantic.
4. Services/Repositories operan sobre la BD vía sesión SQLAlchemy async.
5. La API responde JSON con el código HTTP correspondiente.

## 3. Estado actual del repositorio

- `backend/app/main.py`: define `app = FastAPI(...)`, monta el router
  `app/api/v1/router.py` y expone `GET /health-db` (prueba de conexión).
- `backend/app/core/config.py`: `Settings` (pydantic-settings) lee `.env`
  y expone `ASYNC_DATABASE_URL`.
- `backend/app/db/base.py`: define `Base` (`DeclarativeBase`) — permite
  importar todos los modelos.
- `backend/app/db/session.py`: engine async + `AsyncSessionLocal` + `get_db()`.
- `backend/app/models/`: `user.py` (Role, User), `academic.py` (Career,
  Subject, Topic) y `profiles.py` (Student, Teacher) — 7 tablas en total.
- `backend/alembic/`: `alembic.ini` y `env.py` completos; hay **1 migración
  aplicada** (`crear tablas iniciales`) que creó las 7 tablas en PostgreSQL.
- `backend/app/api/v1/router.py`: `APIRouter(prefix="/api/v1")` con
  `GET /api/v1/ping` de prueba.

### Pendientes
- Modelos faltantes de la guía (aún no modelados): `disponibilidades`,
  `asesorias`, `participantes_asesoria` más las tablas N:M
  (`carrera_materia`, `docente_materia`, `docente_tema`).
- Endpoints CRUD por módulo, schemas Pydantic, services/repositories.
- Autenticación JWT (Fase 2).
- Sin `frontend/`, sin `tests/`, sin commit inicial en git.

## 4. Fases de desarrollo

- [x] Fase 1 — Configuración del backend, conexión async a PostgreSQL,
      modelos Role/User/Carrera/Estudiante/Docente/Materia/Tema y primera
      migración aplicada.
- [ ] Fase 2 — Autenticación JWT y protección de rutas.
- [ ] Fase 3 — Endpoints CRUD (endpoints/schemas/services/repositories).
- [ ] Fase 4 — Frontend React + Vite.
- [ ] Fase 5 — Pruebas (pytest), despliegue y CI/CD.

## 5. Comandos

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Alembic (tras completar `alembic.ini` y `env.py`):

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

Frontend (tras scaffolding):

```bash
npm create vite@latest frontend -- --template react
npm install && npm run dev
```
