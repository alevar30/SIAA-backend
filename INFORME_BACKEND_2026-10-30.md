# Informe de correcciones del backend SIAA

**Fecha:** 30 de octubre de 2026, America/Mexico_City.
**Resultado:** corregidos los problemas de autenticación, altas y configuración
identificados en la revisión. Se añadieron pruebas y documentación operativa.
**Validación final:** 66 pruebas aprobadas, 1 omitida; Ruff y formato aprobados.

## 1. Alcance

Se conservó la arquitectura FastAPI → servicios → repositorios → SQLAlchemy.
La entrega corrige y completa el módulo existente de identidad y altas administrativas.
No se implementaron disponibilidad, asesorías, reservaciones ni frontend; son módulos
pendientes del producto y requieren sus reglas de negocio y contratos específicos.
No se inspeccionó ni modificó un archivo de Figma.

No se hicieron commits ni se publicaron cambios. No se modificó una base externa,
no se crearon usuarios reales ni se restablecieron contraseñas existentes.

## 2. Problemas corregidos

| Problema anterior | Solución | Efecto verificable |
|---|---|---|
| El cambio obligatorio solo se anunciaba | Dependencia `get_ready_user`, aplicada por `require_roles` | Un administrador pendiente de cambio obtiene 403 al intentar dar altas |
| Contraseñas iniciales deducibles del identificador | Generación aleatoria con `secrets.token_urlsafe(18)` | Contraseñas temporales de 24 caracteres y 144 bits aleatorios; solo el hash se guarda |
| Tokens válidos después de cambiar contraseña | Contador `token_version` en BD y claim `ver` en JWT | El token anterior obtiene 401 inmediatamente después del cambio confirmado |
| Instalación incompleta para `EmailStr` | Dependencia explícita `email-validator` | Schemas importan y validan en una instalación nueva |
| Dependencias de hashing distintas al código | Declaración directa de bcrypt; retirada de passlib sin uso | Dependencias reflejan los imports reales |
| Carrera inexistente terminaba en un fallo de BD | Validación de existencia y estado | 404 si no existe; 409 si está desactivada |
| Altas duplicadas/concurrentes sin manejo de errores | Restricciones únicas, captura de `IntegrityError` y rollback | 409 sin cuenta huérfana si falla la inserción del perfil |
| Correo sensible a mayúsculas | Normalización de entradas e índice único sobre `lower(correo)` | Impide altas duplicadas, incluso si una prevalidación pierde una carrera de concurrencia |
| Auth montado dos veces | Un solo montaje mediante el router v1 | Rutas únicas y OpenAPI sin duplicación |
| Swagger anunciaba formulario OAuth2, login recibía JSON | Esquema HTTP Bearer | El contrato de Swagger coincide con el endpoint JSON |
| Sin consulta de usuario actual | `GET /api/v1/auth/me` | React puede reconstruir identidad, rol y perfil tras recargar |
| Sin suite de pruebas | Pruebas de API, seguridad, repositorios, administración y migraciones | Regresión reproducible |

## 3. Refuerzos adicionales

- Verificación de usuario y rol activos en cada petición protegida.
- Los permisos se consultan en BD y no se incluyen como autoridad en el JWT.
- Tokens con firma, expiración, fecha de emisión, sujeto y versión. Se rechazan
  tokens expirados, versiones obsoletas y sujetos inválidos/fuera del rango de BIGINT.
- Actualización de contraseña mediante comparación de versión y aumento atómico:
  una actualización con una sesión obsoleta no puede sobrescribir una más reciente.
- Nueva contraseña de al menos 12 caracteres; límite de 72 bytes UTF-8 validado antes
  de bcrypt. Evita truncamientos y errores con cadenas Unicode largas.
- Se rechaza reutilizar la contraseña actual y se comprueba la confirmación.
- Hashing y verificación bcrypt fuera del bucle asíncrono de las peticiones HTTP.
- Se realiza una comprobación bcrypt también para identificadores inexistentes;
  la contraseña incorrecta no revela si una cuenta está desactivada.
- Los identificadores ambiguos de datos antiguos se rechazan; puede usarse el correo
  inequívoco para entrar mientras se corrigen los datos.
- Validación de longitudes, semestre, ID de carrera y formato de identificadores.
- Relaciones ORM bidireccionales explícitas para evitar relaciones superpuestas.
- Respuestas con tokens, perfil y contraseña temporal incluyen `Cache-Control: no-store`.
- SQL sin parámetros sensibles en logs; `SQL_ECHO` desactivado por defecto.
- URL de PostgreSQL construida con escapado correcto de contraseñas especiales.
- `.env` se localiza respecto de `backend/`, sin depender del directorio de ejecución.
- Validación de clave secreta, algoritmo y duración de los tokens; CORS configurable.
- `/health-db` devuelve 503 con un mensaje genérico ante fallos, sin exponer excepciones,
  hosts ni credenciales; `/health` comprueba el proceso sin necesitar BD.
- Cierre del motor de BD al finalizar la aplicación.
- Herramientas locales `app.manage bootstrap-admin` y `reset-password`, sin rutas HTTP
  nuevas para estas operaciones. El restablecimiento también revoca sesiones.

## 4. Cambios que debe conocer el frontend

1. El login sigue recibiendo JSON con `identificador` y `password`.
2. La respuesta de alta usa **`password_temporal` en lugar de `password_generica`**.
3. Después de cambiar contraseña se responde `requiere_nuevo_login: true`.
   React debe borrar el token anterior y pedir un nuevo login.
4. `/auth/me` devuelve identidad, rol, estado de cambio y los IDs de perfil disponibles.
5. Un token de usuario pendiente de cambio puede consultar `/me` y cambiar contraseña;
   no puede acceder a las altas administrativas.
6. Los duplicados y referencias en conflicto responden **409**; las entradas inválidas,
   **422**; las carreras inexistentes, **404**.
7. Las banderas de login `debe_cambiar_contrasena` y `requiere_cambio_contrasena` se
   conservan por compatibilidad y tienen el mismo valor.
8. En Swagger, ejecutar login y pegar el token en Authorize, sin un formulario OAuth2.

Los cuerpos de ejemplo y el orden de integración están en `README.md`.

## 5. Base de datos y actualización

La migración **`20261030_01`**, posterior a `6569fb796f37`, añade:

- `usuarios.token_version INTEGER NOT NULL DEFAULT 1`.
- Índice único `uq_usuarios_correo_lower` sobre `lower(correo)`.

Antes de aplicarla, buscar correos que solo se diferencien por mayúsculas. Si existen,
la migración no debe decidir cuál cuenta conservar; corresponde revisar sus datos.
El SQL de diagnóstico y los comandos están en el README.

Es necesario aplicar `alembic upgrade head` antes de ejecutar este backend contra una
base existente. Los tokens emitidos con el código anterior se rechazan por carecer de
versión; se requiere un nuevo login. La migración no cambia las contraseñas existentes.
Las cuentas que todavía usen contraseñas iniciales predecibles deben restablecerse con
`app.manage reset-password` y recibir la nueva contraseña por un canal privado.

No se aplicó la migración a una base real durante esta entrega: no hay `.env` local
con conexión configurada y el motor de Docker no estaba activo.

## 6. Verificación realizada

Comando final, desde `backend/`:

```powershell
.venv/Scripts/python.exe -u -m pytest -q --tb=short --basetemp=.test-tmp/run5
```

**Resultado: `66 passed, 1 skipped in 39.30s`.**

La suite verifica, entre otros casos:

- Login con los tres identificadores, mayúsculas de correo y espacios exteriores.
- Credenciales inválidas, tokens ausentes/alterados/expirados y claims inválidos.
- Desactivación de cuenta o rol después de emitir un token.
- Cambio de rol reflejado sin confiar en datos antiguos del token.
- Flujo completo de cambio obligatorio, revocación y nuevo login.
- Cambio incorrecto, confirmación diferente, reutilización y Unicode demasiado largo.
- Actualización rechazada cuando la versión de sesión queda obsoleta.
- Altas de ambos perfiles, contraseña aleatoria y hash almacenado.
- Carrera ausente/inactiva y entradas inválidas.
- Conflictos de unicidad que llegan hasta la BD, con rollback de la cuenta parcial.
- Restricciones de administrador y consulta de perfil sin secretos.
- Respuestas sanitizadas ante fallos SQL y fallos del driver PostgreSQL.
- CORS permitido/denegado, rutas únicas y OpenAPI con Bearer y JSON.
- Primer administrador en una base vacía, rechazo de un segundo bootstrap y reset local.
- Generación del SQL PostgreSQL de todas las migraciones sin conectar a una BD.

Revisión adicional:

```powershell
.venv/Scripts/ruff.exe check app tests alembic
.venv/Scripts/ruff.exe format --check app tests
```

Ambas aprobadas. `git diff --check` también aprobado.

La prueba omitida recorre las migraciones contra PostgreSQL real y compara el esquema
resultante con los modelos. Está lista, junto con `compose.test.yml` y el workflow de
GitHub Actions. **No se afirma que PostgreSQL ni CI se hayan ejecutado con éxito:**
no hubo un servidor PostgreSQL disponible en esta sesión. Las pruebas ejecutadas de
persistencia usaron SQLite con claves foráneas activadas y bases aisladas.

El aislamiento de Windows bloqueaba el socket local interno de `asyncio`. La revisión
automática permitió ejecutar las pruebas fuera de ese aislamiento; los archivos
temporales se mantuvieron en una carpeta ignorada del proyecto.

## 7. Archivos para revisar

- `backend/app/core/deps.py`, `security.py` y `config.py`: acceso, tokens y configuración.
- `backend/app/services/` y `repositories/`: altas transaccionales y cambio de contraseña.
- `backend/app/api/v1/endpoints/`: contratos HTTP y `/auth/me`.
- `backend/app/models/` y nueva migración: contador de versión e integridad del correo.
- `backend/app/manage.py`: administración local de arranque y restablecimiento.
- `backend/tests/`: pruebas ejecutables.
- `backend/requirements*.txt` y `requirements*.lock`: dependencias directas y versiones fijas.
- `.github/workflows/backend.yml` y `backend/compose.test.yml`: verificación con PostgreSQL.
- `README.md`, `PROJECT_WORKFLOW.md`, `AGENTS.md` y nota inicial de la guía: documentación actualizada.

## 8. Pendientes y siguiente paso

Para validar esta entrega contra tu entorno: completar `.env`, revisar duplicados,
aplicar la migración y ejecutar la suite con PostgreSQL. Las instrucciones están listas.

Para el MVP: catálogos consultables, relaciones docentes/materias/temas, disponibilidad,
asesorías individuales y grupales, cupos, reservaciones, cancelaciones e historial.
Las reservas simultáneas requerirán control transaccional específico y pruebas de concurrencia.

Antes de exponerlo públicamente: límites de intentos compartidos, HTTPS, política de
caducidad/entrega de contraseñas temporales, auditoría operativa, monitoreo y respaldos
probados. Estas capacidades no se presentan como implementadas en esta entrega.

El siguiente flujo recomendado es conectar el login y cambio obligatorio de Figma;
después construir disponibilidad → consulta → reserva → mis asesorías con datos reales.
