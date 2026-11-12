# SIAA — backend

API para el Sistema Institucional de Asesorías Académicas. Actualmente implementa
identidad, autenticación y altas administrativas. El frontend previsto es React + Vite.
La disponibilidad, asesorías y reservaciones son trabajo pendiente.

## Preparar el entorno en Windows

Desde `backend/`, con Python 3.12 y uv:

```powershell
uv venv .venv
uv pip sync --python .venv/Scripts/python.exe requirements-dev.lock
Copy-Item .env.example .env
.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

La primera orden solo es necesaria si todavía no existe `.venv`. Completa `.env`
con tu PostgreSQL y coloca la clave generada en `SECRET_KEY`. El marcador del ejemplo
se rechaza deliberadamente. No subas `.env` a Git ni compartas su contenido.

Si prefieres pip: `python -m venv .venv` y
`.venv/Scripts/python.exe -m pip install -r requirements-dev.lock`.
Para un entorno de ejecución sin herramientas de desarrollo utiliza `requirements.lock`.
Los archivos `.txt` expresan dependencias directas y los `.lock` fijan versiones reproducibles.
Los locks se generaron en Windows con Python 3.12; CI comprueba su instalación en Linux.

## Base de datos y primer administrador

Las credenciales deben apuntar a una base creada previamente en PostgreSQL. Con `.env` listo:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.manage bootstrap-admin --correo admin@tuinstitucion.edu --nombre "Administrador SIAA"
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

El comando crea los tres roles si faltan y al primer administrador. Si ya existe uno,
se detiene sin crear otro. Muestra una contraseña temporal aleatoria una sola vez;
entrégala por un canal privado. El administrador también debe cambiarla antes de dar altas.
No hay credenciales predeterminadas ni administrador creado al arrancar la API.

Swagger queda en `http://127.0.0.1:8000/docs`. Primero ejecuta el login, copia
`access_token`, abre **Authorize** y pega únicamente el token. El login usa JSON;
el esquema de Swagger es HTTP Bearer.

## Actualizar una base que ya tiene usuarios

1. Respalda la base e instala las dependencias actualizadas.
2. Busca correos que colisionen al ignorar mayúsculas:

```sql
SELECT lower(correo) AS correo_normalizado, count(*)
FROM usuarios
GROUP BY lower(correo)
HAVING count(*) > 1;
```

Resuelve cada duplicado revisando sus perfiles; no borres cuentas automáticamente.
La migración fallará de forma explícita si existen estos duplicados.

3. Ejecuta `alembic upgrade head` con el entorno del proyecto. La revisión nueva es
   `20261111_01` permite registrar estudiantes antes de que completen su perfil.
   Si aún no aplicaste `20261030_01`, Alembic también añadirá `token_version` y el
   índice único de `lower(correo)`.
4. Reinicia la API con este código. Los tokens antiguos sin versión se rechazan: todos
   deben volver a iniciar sesión.
5. Para cuentas que todavía usan `SIAA-<identificador>`, restablece su contraseña:

```powershell
.venv/Scripts/python.exe -m app.manage reset-password --correo usuario@tuinstitucion.edu
```

El restablecimiento revoca los tokens vigentes y fuerza un cambio con una contraseña
aleatoria nueva. El comando no reactiva cuentas ni roles desactivados. Las cuentas
existentes no se cambian automáticamente por instalar este código.

No hagas downgrade con el backend nuevo ejecutándose: necesita `token_version`.
Si debes revertir, coordina código y esquema desde el respaldo. Un downgrade pierde
el contador y la restricción de correo; no recupera las contraseñas anteriores.

## Contrato para React

| Método y ruta | Acceso | Resultado |
|---|---|---|
| `POST /api/v1/auth/login` | Público | JWT, rol y estado del cambio de contraseña |
| `GET /api/v1/auth/me` | Token válido | Identidad y IDs de perfil, sin hash |
| `POST /api/v1/auth/cambiar-contrasena` | Token válido | Cambio y obligación de nuevo login |
| `GET /api/v1/auth/primer-acceso/carreras` | Estudiante con perfil pendiente | Carreras activas |
| `POST /api/v1/auth/primer-acceso` | Estudiante con perfil pendiente | Guarda el perfil y cambia la contraseña |
| `POST /api/v1/admin/estudiantes` | Administrador con contraseña definitiva | Usuario/perfil y contraseña temporal |
| `POST /api/v1/admin/docentes` | Administrador con contraseña definitiva | Usuario/perfil y contraseña temporal |
| `POST /api/v1/admin/usuarios/{user_id}/restablecer-contrasena` | Administrador con contraseña definitiva | Genera una contraseña temporal nueva y revoca sesiones |
| `GET /health` | Público | Proceso disponible |
| `GET /health-db` | Público | 200 si la BD responde; 503 si falla |
| `GET /api/v1/ping` | Público | Diagnóstico de enrutamiento |

Login:

```json
{"identificador":"20260001","password":"contraseña-entregada"}
```

La respuesta mantiene `debe_cambiar_contrasena` y `requiere_cambio_contrasena` por
compatibilidad; ambos representan el mismo estado. Guarda el token como credencial
sensible y envíalo mediante `Authorization: Bearer <token>`.

Los estudiantes usan su número de control como identificador. El personal puede
usar su correo o, en el caso de docentes, su número de empleado.
Consulta `/auth/me` al restaurar la sesión. Si `requiere_completar_perfil` es
verdadero, muestra el primer acceso. Si solo `debe_cambiar_contrasena` es
verdadero, muestra el cambio de contraseña. El backend bloquea las rutas de
negocio hasta cumplir el requisito correspondiente.

Cambio de contraseña:

```json
{
  "password_actual":"contraseña-entregada",
  "password_nueva":"UnaClaveNuevaLarga123!",
  "password_nueva_confirm":"UnaClaveNuevaLarga123!"
}
```

La nueva contraseña debe tener al menos 12 caracteres y todas las contraseñas
recibidas deben ocupar como máximo 72 bytes UTF-8, límite de bcrypt. Por ejemplo,
las letras acentuadas pueden ocupar más de un byte. No se recortan contraseñas.
Se rechazan confirmaciones distintas y reutilizar la contraseña actual.

Al recibir `requiere_nuevo_login: true`, elimina el token e inicia sesión con la
contraseña nueva. Todos los tokens anteriores del usuario dejan de funcionar.

Alta de estudiante:

```json
{"matricula":"20260001"}
```

En el primer acceso, el estudiante envía `nombre`, `apellidos`, `id_carrera`
y los tres campos del cambio de contraseña a `POST /auth/primer-acceso`.
La carrera debe existir y estar activa. Los estudiantes ya registrados conservan
su perfil. El alta de docente requiere `nombre`, `correo`, `numero_empleado`
y opcionalmente `departamento`. Los identificadores admiten letras ASCII,
números, guion y guion bajo y conservan su capitalización.

Las altas responden 201 con `password_temporal`. Para estudiantes y restablecimientos,
la contraseña temporal es aleatoria y tiene 8 caracteres. Solo se almacena su hash
y se entrega el valor original una vez al administrador que realizó la operación.
El restablecimiento exige un cambio de contraseña y conserva el estado del perfil.
Para cambiar su propia contraseña, el administrador usa la sección Seguridad.

Errores relevantes: 400 para cambio inválido, 401 para credenciales/token inválidos,
403 para rol insuficiente/cuenta desactivada/acceso pendiente, 404 para usuario
inexistente al restablecer, 409 para duplicados o conflictos de estado y 422 para
entradas inválidas.
Los permisos y el estado actual se leen de BD, no del rol que recuerde el frontend.

## Ejecutar pruebas

Desde `backend/`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/ruff.exe check app tests alembic
.venv/Scripts/ruff.exe format --check app tests
```

Por defecto las pruebas crean bases SQLite temporales con claves foráneas activadas;
no conectan a la base de `.env`. La prueba de migraciones PostgreSQL se omite si
`TEST_DATABASE_URL` no está definido.

Para validar con PostgreSQL aislado, con Docker activo:

```powershell
docker compose -f compose.test.yml up -d --wait
$env:TEST_DATABASE_URL = "postgresql+asyncpg://siaa_test:local_test_only@localhost:55432/siaa_test"
.venv/Scripts/python.exe -m pytest -q
Remove-Item Env:TEST_DATABASE_URL
docker compose -f compose.test.yml down
```

El contenedor usa puerto 55432 ligado a localhost y datos de prueba. Cada prueba crea
un esquema aleatorio y lo elimina al finalizar; no uses una base de producción.
La prueba de migraciones recorre upgrade → downgrade → upgrade y compara el esquema
con los modelos. GitHub Actions está preparado para ejecutar el conjunto con PostgreSQL 17.

## Límites actuales

Faltan disponibilidad, asesorías, cupos, reservaciones, cancelación, historial y CRUD de
catálogos/relaciones académicas. No hay integración con el archivo de Figma todavía.
Antes de publicar se requieren HTTPS, límites de intentos compartidos entre instancias,
respaldo/restauración probados, monitoreo y una política de entrega/caducidad de las
contraseñas temporales. Esta entrega corrige la base actual; no certifica producción.


## Frontend integrado

La aplicación React + TypeScript + Vite está en la carpeta vecina `../SIAA-frontend`.
Desde esa carpeta ejecuta `npm ci` y `npm run dev`. En desarrollo, el proxy de Vite
reenvía `/api` a FastAPI en el puerto 8000. No requiere datos ficticios en la aplicación.

Para completar los formularios y listados del frontend se añadieron estas rutas,
restringidas a administradores que ya cambiaron su contraseña temporal:

| Método y ruta | Operación |
|---|---|
| `GET /api/v1/admin/usuarios` | Listado paginado; filtros `rol`, `q`, `page` y `page_size` |
| `GET /api/v1/admin/carreras` | Carreras activas por defecto; `active_only=false` incluye inactivas |
| `POST /api/v1/admin/carreras` | Registrar carrera con `nombre` y `clave` |
| `GET /api/v1/admin/resumen` | Conteos reales de estudiantes, docentes, administradores y carreras activas |

Las consultas no devuelven hashes ni contraseñas. La búsqueda trata `%` y `_` como
caracteres literales y la paginación limita el tamaño de cada consulta.
Aplica `alembic upgrade head` antes de iniciar esta versión del backend.

El frontend tiene login, cambio obligatorio/voluntario de contraseña, perfil, resumen,
listado y altas de estudiantes/docentes, carreras y entrega de contraseña temporal.
Disponibilidad, materias/temas y reservaciones requieren completar sus módulos de backend.
