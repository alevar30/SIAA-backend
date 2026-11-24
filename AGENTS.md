# AGENTS.md

SIAA: Sistema Institucional de Asesorías Académicas. Backend FastAPI + PostgreSQL;
frontend previsto React + Vite. Documentación e interfaz en español.

El autor es estudiante: explica qué cambias y por qué, con ejemplos claros.

## Estado comprobado

- Autenticación JWT, login JSON por correo/matrícula/número de empleado, `/auth/me`,
  cambio de contraseña y altas de estudiantes/docentes restringidas a administrador.
- El acceso a operaciones de negocio requiere `get_ready_user` o `require_roles`;
  `get_current_user` permite el acceso limitado a `/me` y cambio de contraseña.
- Contraseñas temporales aleatorias, bcrypt con límite de 72 bytes UTF-8.
- `token_version` se consulta en BD: cambio o restablecimiento revoca tokens anteriores.
- Trece tablas de dominio y siete migraciones. La aplicación no ejecuta migraciones al iniciar.
  No asumir que una migración está aplicada en una base externa.
- Pruebas en `backend/tests`: SQLite aislado por defecto; PostgreSQL mediante
  `TEST_DATABASE_URL`, con esquemas aleatorios desechables y prueba de migraciones.
- El frontend React + TypeScript + Vite existe en la carpeta vecina `../SIAA-frontend`.
- Hay consultas administrativas de usuarios, carreras y resumen, y alta de carreras.
- Catálogo de materias/temas y relaciones carrera-materia, docente-materia y docente-tema implementados.
- Administración asigna materias; el docente crea temas en ellas, edita los propios y selecciona temas compartidos.
- `temas.id_creador` conserva autoría; los temas anteriores quedan sin autor atribuido y bajo control administrativo.
- Temas con asesorías solo permiten cambios de estado; contenido protegido para conservar historial.
- Las ediciones del catálogo y asignaciones usan `version` para detectar cambios concurrentes.
- Disponibilidad por fecha, asesorías individuales/grupales, reservas, cancelación e historial implementados.
- El docente responsable finaliza sesiones tras su término y registra asistencia.
- Cambios de agenda/cupo bloquean primero la fila del docente; reservas también bloquean estudiante.
- Las fechas exigen zona horaria y se normalizan a UTC; React muestra la zona del dispositivo.
- Git inicializado, con commits previos y `.gitignore`. `.env.example` está versionado;
  `.env` y `.venv` se ignoran. Nunca imprimir credenciales locales.

## Comandos (Windows; desde backend)

```powershell
uv venv .venv # solo al crear el entorno
uv pip sync --python .venv/Scripts/python.exe requirements-dev.lock
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/ruff.exe check app tests alembic
.venv/Scripts/ruff.exe format --check app tests
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

En entornos con temporales restringidos, crear `.test-tmp` y pasar una carpeta
nueva mediante `--basetemp=.test-tmp/identificador-unico` a pytest.

## Convenciones

- Endpoints → validación Pydantic → servicios → repositorios → SQLAlchemy/BD.
- API bajo `/api/v1`, montada una sola vez en `app/main.py`.
- SQLAlchemy async + asyncpg; Alembic usa psycopg síncrono.
- Configuración `POSTGRES_*`, `SECRET_KEY` aleatoria de al menos 32 caracteres;
  `.env` se resuelve respecto de `backend/`, sin depender del directorio actual.
- Las contraseñas temporales se entregan una sola vez en `password_temporal`.
- `app.manage` permite bootstrap del primer administrador y restablecimiento local.
  No ejecutar contra una base externa sin autorización aplicable.
- `README.md` y `PROJECT_WORKFLOW.md` describen el código actual. La guía extensa
  conserva los objetivos/ADR y ejemplos de aprendizaje; no es un inventario actual.
- No cambiar React + Vite (ADR-001). Individual y grupal compartirán `asesorias` (ADR-003).
