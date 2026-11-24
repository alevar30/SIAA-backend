# Arquitectura y flujo actual — SIAA

Actualizado: 23 de noviembre de 2026. Instrucciones operativas: `README.md`.

## Arquitectura

React + TypeScript + Vite (`../SIAA-frontend`) → API REST FastAPI → servicios → repositorios → PostgreSQL.
Pydantic valida entrada y salida. SQLAlchemy usa sesiones asíncronas por petición.
Alembic aplica cambios de esquema; no se usa `create_all` para la base real.

## Funcionalidad implementada

- `POST /api/v1/auth/login`: recibe JSON, devuelve JWT y el estado de cambio obligatorio.
- `GET /api/v1/auth/me`: identidad, rol, perfiles y estado del usuario actual.
- `POST /api/v1/auth/cambiar-contrasena`: valida contraseña actual, nueva y confirmación;
  cambia el hash e incrementa `token_version` de forma atómica. Requiere nuevo login.
- `POST /api/v1/admin/estudiantes` y `/docentes`: solo administrador con contraseña
  definitiva; crea cuenta y perfil en una transacción. Devuelve contraseña temporal aleatoria.
- `/health` verifica el proceso; `/health-db` verifica conexión y responde 503 ante fallo.
- Catálogo y asignación de materias; creación de temas por docentes, edición propia y selección compartida.
- Disponibilidad por fecha, sesiones individuales/grupales, reserva, cancelación, historial y asistencia.

## Autenticación y permisos

1. Se verifica bcrypt fuera del bucle asíncrono principal.
2. El JWT contiene `sub`, `ver`, `iat` y `exp`.
3. Cada petición protegida valida firma, expiración, usuario activo, rol activo y versión en BD.
4. Solo `/me` y cambio de contraseña permiten acceso con cambio obligatorio pendiente.
5. Las operaciones de negocio usan `get_ready_user`/`require_roles`.

Una contraseña cambiada o restablecida invalida los tokens anteriores. Los permisos
se leen de BD; no se confía en un rol enviado por React ni en un rol antiguo en el JWT.

## Persistencia

Trece tablas: identidad y perfiles, catálogo y tres relaciones académicas,
`disponibilidades`, `asesorias` y `participantes_asesoria`.
Siete migraciones; la última es `20261123_03` (autoría de temas).
El índice único `lower(correo)` impide duplicados por mayúsculas, incluso con concurrencia.
Errores de integridad al crear cuentas provocan rollback y respuesta 409.

## Verificación y pendientes

Hay pruebas de seguridad, API, repositorios, administración local y migraciones PostgreSQL.
GitHub Actions ejecutará el conjunto con PostgreSQL cuando se suban estos cambios.

El frontend conecta los flujos de identidad, administración, catálogo, agenda, reserva,
cancelación e historial, conservando la identidad visual existente. Quedan notificaciones
externas y reportes avanzados si forman parte del alcance final. El despliegue de
producción requiere su propia validación operativa.


## Integración con la interfaz

Los listados, selectores y resumen usan `/api/v1/admin/usuarios`, `/carreras` y `/resumen`.
El alta de carreras permite preparar una base vacía para registrar estudiantes sin
escribir IDs manuales. Todas estas operaciones aplican `require_admin`.

Las pruebas de navegador del frontend arrancan un servidor aislado de FastAPI definido
en `backend/tests/e2e_server.py`. Este servidor exige `SIAA_E2E=1` y nunca usa una base real.

## Cierre de jornada — 23 de noviembre de 2026

- Entregado: catálogo y asignaciones, 52 materias de Sistemas sin inglés, agenda,
  asesorías individuales/grupales, reservas, cancelaciones, asistencia e historial.
- El docente crea temas en sus materias asignadas y edita los propios; los temas son
  compartidos por materia. Administración conserva supervisión. Los temas con
  asesorías mantienen su contenido y permiten cambios de estado.
- PostgreSQL local: contenedor `siaa-dev-postgres`, puerto `127.0.0.1:55433`, revisión
  Alembic aplicada `20261123_03`. Los temas anteriores conservan autoría sin atribuir.
- Última verificación: 135 pruebas de backend en PostgreSQL aislado, 19 unitarias de
  frontend y 10 recorridos de navegador aprobados. Build y formato aprobados.
- Corregido el menú para mantener accesible Cerrar sesión en ventanas bajas y móvil.
- Siguiente implementación recomendada: reportes institucionales con filtros por
  fecha, asesorías, asistencia, demanda por materia y actividad docente; después,
  notificaciones internas y gestión de edición/activación de usuarios.
- Pendiente de despliegue: dockerizar frontend/backend, configuración de acceso y
  validación operativa del respaldo/restauración. Los horarios actuales son por fecha.

Para retomar el entorno local, iniciar `docker start siaa-dev-postgres`; desde
`backend/`, ejecutar `.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`;
desde la carpeta `SIAA-frontend`, ejecutar `npm run dev`. Abrir `http://127.0.0.1:5173/`.
Usar las contraseñas vigentes; no restablecer cuentas al iniciar ni usar el servidor
de pruebas para la base habitual. Los respaldos locales se guardan en
`backend/.local-backups/`, excluidos de Git.
