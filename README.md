# SIAA — backend

API para el Sistema Institucional de Asesorías Académicas. Actualmente implementa
identidad, autenticación, administración, catálogo académico, asignaciones docentes,
disponibilidad, asesorías y reservaciones. El frontend React + Vite está integrado.

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

El flujo académico central está implementado. Quedan notificaciones externas,
reportes institucionales avanzados y reglas de recurrencia semanal, si se requieren.
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
También conecta catálogo, asignaciones, agenda, reservas, cancelación y asistencia.


## Catálogo académico y asignaciones docentes

Antes de usar el módulo, aplica `alembic upgrade head` desde `backend/` con el entorno
Python del proyecto. La revisión `20261123_01` añade las relaciones `carrera_materia`,
`docente_materia` y `docente_tema`, versiones de edición y restricciones de integridad.
Los registros anteriores conservan sus datos. Las materias anteriores sin carrera
relacionada pueden vincularse desde Editar materia para incorporarlas a la búsqueda.

Administración dispone de Materias y temas y Asignaciones docentes en el frontend.
Puede crear/editar materias y temas, relacionar una materia con varias carreras,
editar/desactivar carreras y asignar materias a cada docente. El docente dispone de
Mis materias y temas. El estudiante dispone de Buscar docentes con filtros de carrera,
materia y tema. La búsqueda exige que el docente tenga la materia asignada y el tema
seleccionado, y que cuenta, rol y oferta académica estén activos.

| Método y ruta | Operación |
|---|---|
| `GET /api/v1/admin/catalogo/carreras` | Carreras con versión para edición |
| `PUT /api/v1/admin/catalogo/carreras/{id}` | Editar o desactivar carrera |
| `GET, POST /api/v1/admin/catalogo/materias` | Consultar y registrar materias |
| `PUT /api/v1/admin/catalogo/materias/{id}` | Editar materia y sus carreras |
| `GET /api/v1/admin/catalogo/materias/{id}/temas` | Consultar temas administrativos |
| `POST /api/v1/admin/catalogo/temas` | Registrar tema en una materia |
| `PUT /api/v1/admin/catalogo/temas/{id}` | Editar o desactivar tema |
| `GET /api/v1/admin/catalogo/docentes` | Buscar docentes y sus asignaciones |
| `GET /api/v1/admin/catalogo/docentes/{id}` | Consultar asignación y versión |
| `PUT /api/v1/admin/catalogo/docentes/{id}/materias` | Guardar materias autorizadas |
| `GET /api/v1/docente/materias` | Consultar las materias y temas del docente actual |
| `PUT /api/v1/docente/temas` | Guardar temas seleccionados del docente actual |
| `POST /api/v1/docente/temas` | Crear tema en materia asignada; autor obtenido de la sesión |
| `PUT /api/v1/docente/temas/{id}` | Editar tema propio, con comprobación de asignación y versión |
| `GET /api/v1/catalogo/carreras` | Carreras activas para usuarios autenticados |
| `GET /api/v1/catalogo/materias` | Materias activas, con filtro `id_carrera` |
| `GET /api/v1/catalogo/materias/{id}/temas` | Temas activos de una materia disponible |
| `GET /api/v1/catalogo/docentes` | Buscar docentes por `id_materia` e `id_tema`, con paginación |

Las rutas administrativas usan `require_admin` y las propias del docente `require_docente`.
Las consultas académicas usan `get_ready_user`, por lo que se exige completar el primer
perfil y cambiar la contraseña temporal antes de acceder.

Las peticiones PUT incluyen la `version` obtenida al consultar el registro. Una edición
obsoleta obtiene 409 y se debe recargar. En materias se envía `carrera_ids`, en asignaciones
`materia_ids` y en selección docente `tema_ids`. Las dos últimas admiten una lista vacía.
El docente solo modifica su propia selección, cuyo ID se obtiene de la sesión.

Al retirar una materia al docente se eliminan sus selecciones de temas de esa materia
mediante una clave foránea compuesta con CASCADE. Desactivar una carrera, materia o tema
conserva las relaciones y lo excluye de la oferta activa. Un tema mantiene su materia
original. Las claves de materias se normalizan a mayúsculas y se evitan temas duplicados
dentro de la misma materia a través de la API.

Las pruebas verifican restricciones, versiones, migración con datos anteriores y carreras
de concurrencia reales en PostgreSQL. Para ejecutarlas en tu instancia de pruebas define
`TEST_DATABASE_URL`, siempre con un usuario que pueda crear esquemas desechables. La suite
crea y elimina esquemas aleatorios propios. Las pruebas de navegador completas se ejecutan
con `npm run test:e2e` desde el frontend. Sus puertos pueden cambiarse mediante
`SIAA_E2E_FRONTEND_PORT` y `SIAA_E2E_BACKEND_PORT` si ya hay servicios locales en ejecución.

### Materias de la retícula de Sistemas

La retícula proporcionada (plan ISIC-2010-224, especialidad Inteligencia Artificial
Aplicada ISIE-IAA-2022-01) se conserva como datos en
`backend/app/data/reticula_sistemas.json`, con huella SHA-256 del Excel y celdas de origen.
Incluye 52 asignaturas. Los cinco niveles de inglés se excluyen por decisión del usuario.
Las seis actividades de extraescolares,
tutorías, complementarias, servicio social y residencia se documentan aparte y no se
registran como materias para asesorías. Los semestres se conservan como referencia
en el archivo; el catálogo actual registra nombre, clave y carrera.

Desde `backend/`, después de `alembic upgrade head` y con la carrera `ISC` activa:

```powershell
.venv/Scripts/python.exe -m app.seed_systems         # Previsión sin cambios
.venv/Scripts/python.exe -m app.seed_systems --apply # Registrar en una transacción
```

Puede usarse `--carrera OTRA_CLAVE` para una carrera existente. Repetir la carga no
duplica registros ni elimina relaciones con otras carreras. Si una clave existente
tiene otro nombre o está inactiva, el lote se cancela para revisar el conflicto.
Las materias quedan disponibles a través de las rutas habituales del catálogo y
de asignación docente, sin configurar listas separadas en el frontend.

## Agenda, asesorías y reservas — entrega de noviembre de 2026

La migración `20261123_02` agrega `disponibilidades`, `asesorias` y
`participantes_asesoria` sin reemplazar tablas ni registros anteriores. Aplicar
`.venv/Scripts/python.exe -m alembic upgrade head` y reiniciar FastAPI antes de usar
las pantallas nuevas.

### Recorrido para probar

1. Administración registra materias del catálogo y las asigna a un docente.
2. El docente crea temas o selecciona temas compartidos en **Mis materias y temas**.
3. En **Mi disponibilidad** publica un bloque por fecha, presencial (aula) o virtual
   (enlace HTTP(S)). Desde el bloque abre **Crear asesoría**, elige tema e intervalo,
   y publica una sesión individual o grupal.
4. El estudiante entra en **Buscar asesorías**, filtra por materia, abre una sesión
   y confirma su reserva. También puede llegar desde **Buscar docentes** con el
   docente y tema ya filtrados.
5. En **Mis asesorías** consulta próximas sesiones, cancela su lugar antes del inicio
   o revisa su historial. El docente consulta la lista de participantes.
6. El docente puede cancelar la sesión con motivo mientras no haya terminado. Se
   cancelan sus reservas y el motivo aparece en el historial de los participantes.
7. Después de la hora de término, el docente marca quienes asistieron y confirma
   **Guardar asistencia y finalizar**. Los no marcados quedan como «No asistió».
8. Administración consulta todas las sesiones en **Agenda institucional** y puede
   cancelarlas con motivo. La asistencia corresponde al docente responsable.

### Reglas implementadas

- Disponibilidad por fecha con anticipación de hasta 180 días y duración entre
  15 minutos y 8 horas. Las asesorías duran entre 15 minutos y 4 horas, siempre
  dentro de una disponibilidad activa del mismo docente.
- Individual: un lugar. Grupal: entre 2 y 50. No se permite publicar con un tema
  ajeno, inactivo o sin materia/carrera activa.
- No hay cruces de disponibilidad activa ni de sesiones del mismo docente. Los
  intervalos contiguos están permitidos. Un estudiante tampoco puede reservar
  asesorías de diferentes docentes en horarios superpuestos.
- Solo el estudiante propietario cancela su reserva. Solo el docente responsable
  publica/finaliza; administración también puede cancelar sesiones.
- La reserva se cierra al iniciar la sesión. Cancelar libera el cupo. Volver a
  reservar reutiliza la participación con nueva versión; repetir una reserva ya
  confirmada no crea filas adicionales.
- Retirar disponibilidad requiere cancelar o finalizar sus asesorías programadas.
  Para cambiar una sesión publicada se cancela y se crea otra, conservando historial.
- Cupo y cruces se verifican bajo bloqueo transaccional en PostgreSQL: docente,
  asesoría y, al reservar, estudiante. La combinación asesoría/estudiante es única.
  Los cambios usan versiones para rechazar peticiones obsoletas con 409.
- Los estudiantes no reciben matrículas ni nombres de otros participantes. El enlace
  virtual se entrega únicamente al responsable, administración o quienes tienen
  reserva vigente. Las bajas del catálogo ocultan la oferta nueva, conservando
  consultas y cancelaciones de reservas anteriores.
- Las entradas requieren fecha/hora con zona; se normalizan a UTC. El navegador
  convierte las entradas locales y muestra explícitamente la zona del dispositivo.

### Contratos principales

Todas las rutas requieren autenticación y haber completado el primer acceso.

| Método y ruta bajo `/api/v1` | Acceso y operación |
|---|---|
| `GET, POST /docente/disponibilidades` | Horarios propios del docente |
| `PUT /docente/disponibilidades/{id}/cancelar` | Retirar bloque con `version` |
| `POST /docente/asesorias` | Publicar sesión propia |
| `GET /asesorias/disponibles` | Oferta activa; filtros docente, materia, tema y paginación |
| `GET /asesorias/mias` | Agenda propia o institucional; `vista=proximas` o `historial` |
| `GET /asesorias/{id}` | Detalle; participantes solo para responsable/administración |
| `POST /asesorias/{id}/reservar` | Reservar como estudiante |
| `PUT /asesorias/{id}/cancelar-reserva` | Cancelar reserva propia con `version` |
| `PUT /asesorias/{id}/cancelar` | Cancelar sesión con `version` y `motivo` |
| `PUT /asesorias/{id}/finalizar` | Cerrar sesión con `version` y lista `asistieron` de IDs de estudiantes |

La cancelación se informa dentro de la aplicación; no envía correo ni notificaciones
push. Los bloques son por fecha, sin repetición semanal automática. No se agregan
sesiones, temas ni usuarios ficticios a la base habitual para probar esta entrega.

### Validación de esta entrega

- Backend: 127 pruebas aprobadas en PostgreSQL 17 aislado, sin omisiones. Incluyen
  migraciones upgrade/downgrade, conservación de datos, permisos y conflictos.
- Concurrencia real: último lugar individual/grupal, horarios/sesiones simultáneos
  y reserva del mismo estudiante con diferentes docentes en un horario superpuesto.
- Frontend: 19 pruebas unitarias y 9 recorridos de navegador aprobados, incluyendo
  regresión de acceso, primer perfil, catálogo, asignaciones y el flujo nuevo.
- Compilación TypeScript/Vite, Ruff y formato de los archivos modificados aprobados.
- Vistas nuevas revisadas en escritorio y móvil; controles de accesibilidad sin
  infracciones y sin desbordamiento horizontal en la reserva móvil.
- Migración aplicada en PostgreSQL local, revisión `20261123_02`. Se comprobaron
  los conteos antes/después: permanecen las 52 materias y los datos existentes.

El siguiente trabajo funcional puede centrarse en reportes institucionales y
notificaciones. La agenda disponible en esta entrega usa fechas concretas y conserva
el historial; no incluye programación semanal automática ni avisos externos.

## Temas creados por docentes — autoría y supervisión

La creación cotidiana de temas se realiza en **Mis materias y temas** del docente:

1. Administración asigna la materia.
2. El docente pulsa **Nuevo tema**, completa nombre y descripción, y guarda.
3. Selecciona ese tema (o uno compartido por otro docente) y pulsa **Guardar temas**
   para ofrecer asesorías sobre él. Crear no selecciona automáticamente el tema.
4. **Editar tema** solo aparece en temas creados por el usuario actual. La edición
   también exige conservar la asignación de la materia y usar su versión vigente.

Los temas pertenecen a la materia y se comparten entre sus docentes: no se crean
copias por docente. Las creaciones concurrentes se serializan por materia para
rechazar nombres duplicados, incluso si cambian mayúsculas o espacios al principio/final.
Crear o reactivar requiere materia y carrera activas. La API rechaza campos de autor
enviados por el cliente y obtiene `id_creador` del usuario autenticado.

Administración conserva la supervisión y puede corregir/desactivar temas de cualquier
autor, además del alta administrativa de apoyo existente. Si el tema ya tiene alguna
asesoría (también cancelada o finalizada), su nombre y descripción no se pueden
cambiar: se conserva el contenido del historial y solo se permite cambiar su estado.
Para contenido diferente se crea otro tema. No se eliminan temas ni asesorías.

La migración `20261123_03` añade la referencia nullable `temas.id_creador`. Los temas
anteriores permanecen con sus IDs, nombres, selecciones y asesorías; su autor queda
sin atribuir porque no puede inferirse de los datos previos. Administración puede
gestionarlos y los docentes pueden seleccionarlos, pero no apropiarse de su edición.
Las respuestas incluyen autor, nombre del autor y `tiene_asesorias` para mostrar los
permisos y el estado del contenido. Estos permisos siempre se comprueban en backend.

Antes de crear o editar desde el frontend se debe guardar o cancelar cualquier
selección pendiente, evitando perder cambios al recargar los temas.

Validación de autoría: 135 pruebas de backend aprobadas en PostgreSQL aislado y
19 pruebas unitarias del frontend. Se verificó en navegador la creación/edición
propia, rechazo de duplicados, selección por un segundo docente y búsqueda por el
estudiante, además de la regresión de catálogo y agenda. La vista móvil y el formulario
pasaron los controles de accesibilidad. La migración local conservó las 52 materias,
los dos temas anteriores y los demás registros, sin atribuir autores ficticios.
