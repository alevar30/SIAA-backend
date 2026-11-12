# Arquitectura y flujo actual — SIAA

Actualizado: 30 de octubre de 2026. Instrucciones operativas: `README.md`.

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

## Autenticación y permisos

1. Se verifica bcrypt fuera del bucle asíncrono principal.
2. El JWT contiene `sub`, `ver`, `iat` y `exp`.
3. Cada petición protegida valida firma, expiración, usuario activo, rol activo y versión en BD.
4. Solo `/me` y cambio de contraseña permiten acceso con cambio obligatorio pendiente.
5. Las operaciones de negocio usan `get_ready_user`/`require_roles`.

Una contraseña cambiada o restablecida invalida los tokens anteriores. Los permisos
se leen de BD; no se confía en un rol enviado por React ni en un rol antiguo en el JWT.

## Persistencia

Tablas: `roles`, `usuarios`, `estudiantes`, `docentes`, `carreras`, `materias`, `temas`.
Tres migraciones: base, campos de contraseña y versión de tokens/índice de correo.
El índice único `lower(correo)` impide duplicados por mayúsculas, incluso con concurrencia.
Errores de integridad al crear cuentas provocan rollback y respuesta 409.

## Verificación y pendientes

Hay pruebas de seguridad, API, repositorios, administración local y migraciones PostgreSQL.
GitHub Actions ejecutará el conjunto con PostgreSQL cuando se suban estos cambios.

Faltan catálogos consultables, relaciones N:M, disponibilidad, asesorías, participantes,
reservaciones, cancelación e historial. El frontend ya conecta autenticación, perfiles, usuarios y carreras; conserva la identidad visual de Figma.
No se considera un MVP completo ni un despliegue listo para producción.


## Integración con la interfaz

Los listados, selectores y resumen usan `/api/v1/admin/usuarios`, `/carreras` y `/resumen`.
El alta de carreras permite preparar una base vacía para registrar estudiantes sin
escribir IDs manuales. Todas estas operaciones aplican `require_admin`.

Las pruebas de navegador del frontend arrancan un servidor aislado de FastAPI definido
en `backend/tests/e2e_server.py`. Este servidor exige `SIAA_E2E=1` y nunca usa una base real.
