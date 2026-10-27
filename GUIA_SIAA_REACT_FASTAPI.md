# SIAA — Guía de desarrollo con React, FastAPI y PostgreSQL

> **Proyecto:** Sistema Institucional de Asesorías Académicas (SIAA)  
> **Objetivo técnico:** construir una aplicación web mantenible, segura y preparada para evolucionar a producción.  
> **Objetivo de aprendizaje:** entender cada capa del sistema en lugar de limitarse a copiar código.

---

# 1. Objetivo del proyecto

SIAA busca centralizar la gestión de asesorías académicas dentro de una institución.

El sistema permitirá, de manera gradual:

- Registrar y autenticar usuarios.
- Manejar roles como estudiante, docente y administrador.
- Registrar carreras, materias y temas.
- Relacionar docentes con las materias y temas que pueden asesorar.
- Permitir que los docentes definan sus horarios disponibles.
- Permitir que los estudiantes busquen asesorías.
- Reservar asesorías individuales.
- Crear y reservar asesorías grupales.
- Controlar cupos.
- Consultar historial de asesorías.
- En etapas posteriores, agregar notificaciones, evaluaciones, foro, reportes y estadísticas.

El proyecto se desarrollará primero como un **MVP (Producto Mínimo Viable)** y después se irá fortaleciendo hasta tener características necesarias para producción.

---

# 2. Arquitectura general

React y FastAPI son compatibles y cumplen funciones distintas.

```text
┌─────────────────────────────────────┐
│              FRONTEND               │
│                                     │
│          React + Vite               │
│                                     │
│  - Interfaces                       │
│  - Formularios                      │
│  - Dashboard                        │
│  - Calendarios                      │
│  - Validación visual                │
└─────────────────┬───────────────────┘
                  │
                  │ HTTP / HTTPS
                  │ JSON
                  │ Fetch API
                  ▼
┌─────────────────────────────────────┐
│               BACKEND               │
│                                     │
│              FastAPI                │
│                                     │
│  - API REST                         │
│  - Reglas de negocio                │
│  - Autenticación                    │
│  - Autorización                     │
│  - Validaciones                     │
└─────────────────┬───────────────────┘
                  │
                  │ SQLAlchemy
                  ▼
┌─────────────────────────────────────┐
│            BASE DE DATOS            │
│                                     │
│             PostgreSQL              │
│                                     │
│  - Usuarios                         │
│  - Estudiantes                      │
│  - Docentes                         │
│  - Materias                         │
│  - Asesorías                        │
│  - Participantes                    │
│  - etc.                             │
└─────────────────────────────────────┘
```

## Responsabilidades

### React

React será responsable de la interfaz:

- Mostrar información.
- Capturar formularios.
- Navegar entre páginas.
- Consumir la API.
- Mostrar mensajes de error y éxito.
- Administrar el estado de la interfaz.

React **no debe acceder directamente a PostgreSQL**.

### FastAPI

FastAPI será responsable de:

- Recibir peticiones HTTP.
- Validar datos.
- Aplicar reglas de negocio.
- Autenticar usuarios.
- Autorizar acciones por rol.
- Consultar o modificar la base de datos.
- Responder con JSON.

### PostgreSQL

PostgreSQL será responsable de almacenar permanentemente la información del sistema.

---

# 3. Stack propuesto

## Frontend

- React
- Vite
- JavaScript
- CSS
- Fetch API
- React Router cuando se necesite navegación

Para aprender, no es necesario agregar Redux al inicio.

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy 2
- Alembic

## Base de datos

- PostgreSQL

Para un proyecto que llegará a producción conviene utilizar una versión de PostgreSQL que se encuentre oficialmente soportada y mantenerla actualizada en sus versiones menores.

## Seguridad

- Hash de contraseñas con Argon2 o bcrypt.
- JWT o sesiones seguras para autenticación.
- Variables de entorno.
- CORS configurado explícitamente.
- HTTPS en producción.
- Separación entre autenticación y autorización.

## Pruebas y herramientas

- Pytest para backend.
- Postman o Bruno para probar API manualmente.
- Swagger/OpenAPI incluido por FastAPI.
- Vitest para pruebas del frontend si se incorpora posteriormente.
- Git y GitHub.
- Docker en una etapa posterior.
- GitHub Actions u otra herramienta de CI/CD en una etapa posterior.

---

# 4. Modelo de datos base del MVP

El modelo inicial contempla las siguientes entidades.

## Entidades principales

1. `roles`
2. `usuarios`
3. `carreras`
4. `estudiantes`
5. `docentes`
6. `materias`
7. `carrera_materia`
8. `temas`
9. `docente_materia`
10. `docente_tema`
11. `disponibilidades`
12. `asesorias`
13. `participantes_asesoria`

## Relaciones principales

```text
ROLES 1:N USUARIOS

USUARIOS 1:0..1 ESTUDIANTES
USUARIOS 1:0..1 DOCENTES

CARRERAS 1:N ESTUDIANTES

CARRERAS N:M MATERIAS
mediante CARRERA_MATERIA

MATERIAS 1:N TEMAS

DOCENTES N:M MATERIAS
mediante DOCENTE_MATERIA

DOCENTES N:M TEMAS
mediante DOCENTE_TEMA

DOCENTES 1:N DISPONIBILIDADES

DOCENTES 1:N ASESORIAS
MATERIAS 1:N ASESORIAS
TEMAS 1:N ASESORIAS

ASESORIAS N:M ESTUDIANTES
mediante PARTICIPANTES_ASESORIA
```

Una asesoría individual y una asesoría grupal pueden almacenarse en la misma tabla `asesorias`.

La diferencia se controla mediante campos como:

```text
tipo = INDIVIDUAL | GRUPAL
cupo_maximo
```

Los estudiantes registrados se almacenan en `participantes_asesoria`.

---

# 5. Estructura propuesta del repositorio

```text
SIAA/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── usuarios.py
│   │   │   │   ├── estudiantes.py
│   │   │   │   ├── docentes.py
│   │   │   │   ├── carreras.py
│   │   │   │   ├── materias.py
│   │   │   │   ├── temas.py
│   │   │   │   ├── disponibilidades.py
│   │   │   │   └── asesorias.py
│   │   │   │
│   │   │   └── router.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── exceptions.py
│   │   │
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── init_db.py
│   │   │
│   │   ├── models/
│   │   │   ├── role.py
│   │   │   ├── usuario.py
│   │   │   ├── estudiante.py
│   │   │   ├── docente.py
│   │   │   ├── carrera.py
│   │   │   ├── materia.py
│   │   │   ├── tema.py
│   │   │   ├── disponibilidad.py
│   │   │   ├── asesoria.py
│   │   │   └── participante_asesoria.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── usuario.py
│   │   │   ├── estudiante.py
│   │   │   ├── docente.py
│   │   │   ├── carrera.py
│   │   │   ├── materia.py
│   │   │   ├── tema.py
│   │   │   ├── disponibilidad.py
│   │   │   └── asesoria.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── usuario_service.py
│   │   │   ├── disponibilidad_service.py
│   │   │   └── asesoria_service.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── usuario_repository.py
│   │   │   ├── docente_repository.py
│   │   │   └── asesoria_repository.py
│   │   │
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   │
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── forms/
│   │   │   └── layout/
│   │   │
│   │   ├── pages/
│   │   │   ├── Login/
│   │   │   ├── Dashboard/
│   │   │   ├── Asesorias/
│   │   │   ├── Disponibilidad/
│   │   │   └── Perfil/
│   │   │
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── authService.js
│   │   │   └── asesoriaService.js
│   │   │
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── utils/
│   │   ├── styles/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│   ├── arquitectura.md
│   ├── der.md
│   ├── api.md
│   └── decisiones.md
│
├── .gitignore
├── README.md
└── docker-compose.yml        # agregar en una etapa posterior
```

No es obligatorio crear todos estos archivos desde el primer día.

La estructura se irá creando conforme el proyecto la necesite.

---

# 6. Creación inicial de carpetas

Desde una terminal:

```bash
mkdir SIAA
cd SIAA

mkdir backend
mkdir docs
```

El frontend se generará posteriormente utilizando Vite.

Inicializar Git:

```bash
git init
```

Crear un `.gitignore` en la raíz.

Contenido sugerido:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Variables de entorno
.env

# Node
node_modules/
dist/

# IDE
.vscode/
.idea/

# Sistema operativo
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
```

Primer commit:

```bash
git add .
git commit -m "chore: initial project structure"
```

---

# 7. Estrategia de aprendizaje

No construiremos todo simultáneamente.

El proyecto avanzará por fases.

Cada fase tendrá:

1. **Qué aprender.**
2. **Qué construir.**
3. **Cómo probarlo.**
4. **Criterio para avanzar.**

Una regla útil será:

> Si no podemos explicar cómo funciona una fase y demostrarla mediante una prueba, todavía no está terminada.

---

# FASE 0 — Preparar el entorno

## Objetivo

Tener instaladas las herramientas necesarias.

## Instalar

- Git
- Python
- Node.js
- PostgreSQL
- Un editor como Visual Studio Code
- Postman o una herramienta equivalente

Comprobar:

```bash
git --version
python --version
node --version
npm --version
psql --version
```

## Aprendizaje

Antes de continuar deben entender qué función tiene cada herramienta.

```text
Git          → control de versiones
Python       → lenguaje del backend
FastAPI      → API
Node/npm     → herramientas necesarias para React
React        → frontend
PostgreSQL   → base de datos
```

## Prueba de la fase

Todos los comandos anteriores deben responder correctamente.

## Criterio para avanzar

Cada integrante puede:

- clonar el repositorio;
- abrirlo;
- ejecutar Git;
- ejecutar Python;
- ejecutar Node;
- conectarse a PostgreSQL.

---

# FASE 1 — Crear el backend mínimo

## Objetivo

Ejecutar por primera vez FastAPI.

Entrar a:

```bash
cd SIAA/backend
```

Crear entorno virtual:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instalar inicialmente:

```bash
pip install fastapi uvicorn
```

Crear:

```text
backend/
└── app/
    ├── __init__.py
    └── main.py
```

`main.py`:

```python
from fastapi import FastAPI

app = FastAPI(
    title="SIAA API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "SIAA API funcionando"}
```

Ejecutar:

```bash
uvicorn app.main:app --reload
```

Abrir:

```text
http://localhost:8000
```

También:

```text
http://localhost:8000/docs
```

FastAPI genera documentación OpenAPI interactiva automáticamente.

## Qué aprender

- Qué es HTTP.
- Qué es una API.
- Qué es un endpoint.
- Qué significa GET.
- Qué es JSON.
- Qué representa un código HTTP 200.

## Cómo probar

### Navegador

Entrar a:

```text
http://localhost:8000/
```

Esperado:

```json
{
  "message": "SIAA API funcionando"
}
```

### Swagger

Entrar a:

```text
http://localhost:8000/docs
```

Ejecutar `GET /`.

## Criterio para avanzar

El backend responde correctamente y todos pueden explicar:

```text
navegador → petición HTTP → FastAPI → respuesta JSON
```

---

# FASE 2 — Configuración y variables de entorno

## Objetivo

Evitar colocar configuraciones sensibles directamente en el código.

Instalar:

```bash
pip install pydantic-settings
```

Crear:

```text
backend/
├── .env
├── .env.example
└── app/
    └── core/
        └── config.py
```

Ejemplo `.env.example`:

```env
APP_NAME=SIAA API
APP_ENV=development
DATABASE_URL=postgresql+psycopg://siaa_user:password@localhost:5432/siaa
SECRET_KEY=cambiar_en_cada_entorno
FRONTEND_URL=http://localhost:5173
```

Nunca subir `.env` a Git.

Sí subir `.env.example`, sin secretos reales.

## Qué aprender

- Variables de entorno.
- Separación configuración/código.
- Desarrollo, pruebas y producción.
- Por qué las contraseñas no deben estar en Git.

## Cómo probar

Temporalmente crear un endpoint que muestre solamente datos no sensibles, como:

```json
{
  "environment": "development"
}
```

Nunca devolver `SECRET_KEY` o contraseñas.

## Criterio para avanzar

La aplicación puede arrancar con configuración tomada del entorno.

---

# FASE 3 — Crear PostgreSQL y conectar FastAPI

## Objetivo

Lograr comunicación:

```text
FastAPI → SQLAlchemy → PostgreSQL
```

Instalar:

```bash
pip install sqlalchemy alembic psycopg
```

Crear una base de datos para desarrollo.

Ejemplo conceptual:

```sql
CREATE DATABASE siaa;
```

En un entorno real es preferible utilizar un usuario de base de datos específico para la aplicación, con los permisos estrictamente necesarios.

Crear:

```text
app/
└── db/
    ├── base.py
    └── session.py
```

En SQLAlchemy 2 se recomienda trabajar con el estilo moderno de modelos declarativos y `mapped_column`.

## Qué aprender

- Qué es una conexión.
- Qué es un ORM.
- Qué es una sesión de SQLAlchemy.
- Diferencia entre modelo ORM y esquema Pydantic.
- Qué es una transacción.

## Primera prueba

Crear un endpoint sencillo de comprobación que ejecute:

```sql
SELECT 1;
```

Si responde correctamente:

```json
{
  "database": "ok"
}
```

la conexión básica funciona.

## Criterio para avanzar

FastAPI se conecta correctamente a PostgreSQL sin guardar credenciales en el código.

---

# FASE 4 — Crear modelos SQLAlchemy

## Objetivo

Transformar el DER en modelos.

No crear todos los modelos al mismo tiempo.

Orden recomendado:

```text
1. Role
2. Usuario
3. Carrera
4. Estudiante
5. Docente
6. Materia
7. Tema
8. CarreraMateria
9. DocenteMateria
10. DocenteTema
11. Disponibilidad
12. Asesoria
13. ParticipanteAsesoria
```

## Qué aprender con cada modelo

Por ejemplo, al crear `Usuario` estudiar:

- PK.
- FK.
- `unique`.
- `nullable`.
- índices.
- relaciones ORM.
- tipos SQL.

Ejemplo conceptual:

```python
class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = mapped_column(primary_key=True)
    nombre = mapped_column(...)
    correo = mapped_column(..., unique=True)
    password_hash = mapped_column(...)
    id_rol = mapped_column(ForeignKey("roles.id_rol"))
```

No copiar el ejemplo sin comprender los tipos y restricciones que necesita cada campo.

## Pruebas

Por cada modelo comprobar:

- La tabla se genera.
- La PK funciona.
- Las FK funcionan.
- Los campos `UNIQUE` rechazan duplicados.
- Los campos obligatorios rechazan valores nulos.

## Criterio para avanzar

El modelo físico coincide con el DER aprobado.

---

# FASE 5 — Introducir Alembic correctamente

## Objetivo

Administrar cambios de estructura de la base de datos mediante migraciones.

Inicializar:

```bash
alembic init alembic
```

Configurar Alembic para utilizar los modelos de SQLAlchemy.

Crear una migración:

```bash
alembic revision --autogenerate -m "create initial tables"
```

Revisar el archivo generado.

Después:

```bash
alembic upgrade head
```

Comprobar historial:

```bash
alembic history
```

## Regla importante

No ejecutar una migración autogenerada sin revisarla.

Alembic puede detectar muchos cambios, pero la responsabilidad final sigue siendo del equipo.

## Qué aprender

- Qué es una migración.
- Por qué no debemos modificar una base de producción manualmente.
- Upgrade.
- Downgrade.
- Versionado del esquema.

## Prueba

1. Crear la base vacía.
2. Ejecutar `alembic upgrade head`.
3. Revisar que aparezcan todas las tablas.
4. Ejecutar pruebas de restricciones.

## Criterio para avanzar

Un miembro del equipo puede descargar el repositorio, crear una base vacía y reconstruir el esquema únicamente usando Alembic.

---

# FASE 6 — Crear la primera API CRUD

## Objetivo

Aprender el flujo completo con una entidad sencilla.

Comenzar por `carreras` o `materias`.

Implementar:

```text
POST   /api/carreras
GET    /api/carreras
GET    /api/carreras/{id}
PATCH  /api/carreras/{id}
DELETE /api/carreras/{id}
```

Para producción puede ser preferible realizar borrado lógico utilizando un campo como `activo`, según la entidad.

## Arquitectura interna

```text
route
  ↓
service
  ↓
repository
  ↓
SQLAlchemy
  ↓
PostgreSQL
```

### Route

Maneja HTTP.

### Service

Contiene reglas de negocio.

### Repository

Contiene acceso a datos.

Para un MVP pequeño esta separación puede parecer más código, pero ayuda a aprender responsabilidades y a evitar rutas enormes.

## Qué aprender

- GET.
- POST.
- PATCH.
- DELETE.
- Código 200.
- Código 201.
- Código 204.
- Código 400.
- Código 404.
- Validación con Pydantic.

## Pruebas manuales

Usar Swagger o Postman.

### Crear

```http
POST /api/carreras
```

```json
{
  "nombre": "Ingeniería en Sistemas",
  "clave": "ISC"
}
```

### Consultar

```http
GET /api/carreras
```

### Error esperado

Intentar crear una clave duplicada.

La API debe devolver un error controlado y no un traceback interno.

## Criterio para avanzar

CRUD completo funcionando y errores conocidos manejados adecuadamente.

---

# FASE 7 — Pruebas automatizadas del backend

## Objetivo

Dejar de depender únicamente de pruebas manuales.

Instalar:

```bash
pip install pytest httpx
```

Crear:

```text
backend/tests/
├── unit/
├── integration/
└── conftest.py
```

Ejemplos que deben automatizarse:

```text
✓ crear una carrera válida
✓ impedir una clave duplicada
✓ consultar una carrera existente
✓ devolver 404 para una inexistente
✓ modificar una carrera
```

Ejecutar:

```bash
pytest
```

## Regla del proyecto

Cada bug importante corregido debería producir una prueba que evite que vuelva a aparecer.

## Criterio para avanzar

Las pruebas se ejecutan localmente y pasan consistentemente.

---

# FASE 8 — Usuarios y autenticación

## Objetivo

Implementar registro/login de forma segura.

Nunca guardar:

```text
password = "123456"
```

Guardar solamente un hash:

```text
password_hash = "..."
```

Flujo:

```text
Usuario escribe contraseña
        ↓
FastAPI
        ↓
algoritmo de hash
        ↓
password_hash
        ↓
PostgreSQL
```

Para login:

```text
correo + contraseña
        ↓
buscar usuario
        ↓
verificar hash
        ↓
crear autenticación
        ↓
responder al cliente
```

## Endpoints iniciales

```text
POST /api/auth/login
GET  /api/auth/me
```

El registro de usuarios debe definirse según las reglas institucionales.

Por ejemplo, podría ser realizado por administración, importación institucional o registro controlado.

## Qué aprender

- Hash.
- Diferencia entre cifrado y hash.
- Token.
- JWT.
- Claims.
- Expiración.
- Autenticación.
- Autorización.

## Pruebas

```text
✓ contraseña correcta permite login
✓ contraseña incorrecta rechaza login
✓ usuario inexistente rechaza login
✓ endpoint protegido rechaza usuario no autenticado
✓ usuario autenticado puede consultar /me
```

## Seguridad

No registrar contraseñas en logs.

No retornar `password_hash` en respuestas de API.

## Criterio para avanzar

Un usuario puede autenticarse y acceder a un endpoint protegido.

---

# FASE 9 — Roles y autorización

## Objetivo

Diferenciar permisos.

Ejemplo:

```text
ESTUDIANTE
- consultar materias
- consultar docentes
- consultar asesorías
- reservar
- cancelar su participación

DOCENTE
- administrar disponibilidad
- consultar sus asesorías
- crear asesorías grupales
- administrar sesiones asignadas

ADMINISTRADOR
- administrar catálogos
- administrar usuarios
- consultar información institucional
```

## Importante

Ocultar un botón en React **no es seguridad**.

Ejemplo:

```text
React oculta "Eliminar usuario"
```

pero FastAPI también debe comprobar el rol.

## Pruebas

```text
✓ estudiante no puede ejecutar endpoint de administrador
✓ docente no puede modificar disponibilidad de otro docente
✓ administrador sí puede acceder al endpoint administrativo
```

Esperado:

```text
403 Forbidden
```

cuando existe autenticación pero no autorización.

---

# FASE 10 — Disponibilidad de docentes

## Objetivo

Permitir que un docente defina cuándo puede dar asesorías.

Ejemplo:

```json
{
  "dia_semana": 1,
  "hora_inicio": "10:00",
  "hora_fin": "12:00",
  "duracion_minutos": 30,
  "modalidad": "PRESENCIAL"
}
```

## Reglas a validar

- `hora_inicio < hora_fin`.
- Duración mayor que cero.
- Solo el docente propietario puede modificarla.
- Evitar reglas evidentemente duplicadas.
- Validar modalidad.

## Pruebas

```text
✓ disponibilidad válida
✓ inicio posterior al fin → error
✓ usuario ajeno intenta editar → 403
✓ docente consulta sus horarios
```

---

# FASE 11 — Lógica central de asesorías

Esta fase es una de las más importantes.

## Crear una asesoría

Una asesoría contiene:

```text
docente
materia
tema
tipo
fecha
hora_inicio
hora_fin
modalidad
cupo_maximo
estado
```

## Validaciones

Antes de crearla:

```text
1. El docente existe.
2. La materia existe.
3. El tema pertenece a la materia.
4. El docente puede asesorar esa materia/tema.
5. La hora inicial es menor a la final.
6. No existe un conflicto con otra asesoría.
7. El tipo es INDIVIDUAL o GRUPAL.
8. El cupo es coherente con el tipo.
```

## Estados posibles

Ejemplo inicial:

```text
PROGRAMADA
CANCELADA
FINALIZADA
```

Conviene evitar valores libres escritos arbitrariamente.

Pueden utilizarse enums o restricciones.

---

# FASE 12 — Reservar una asesoría

## Objetivo

Crear registros en:

```text
participantes_asesoria
```

Flujo:

```text
Estudiante solicita reservar
        ↓
FastAPI recibe petición
        ↓
verifica autenticación
        ↓
comprueba asesoría
        ↓
comprueba cupo
        ↓
comprueba duplicado
        ↓
registra participación
        ↓
confirma
```

## Restricción importante

Agregar:

```text
UNIQUE(id_asesoria, id_estudiante)
```

para impedir que un estudiante esté registrado dos veces en la misma asesoría.

## Concurrencia

Hay un problema importante:

```text
Queda 1 lugar.

Estudiante A consulta → ve 1 lugar.
Estudiante B consulta → ve 1 lugar.

A reserva.
B reserva casi al mismo tiempo.
```

Una implementación ingenua podría aceptar ambos.

Por eso el control de cupo no debe depender solamente de React.

Debe aplicarse en backend dentro de una transacción adecuada y apoyarse en restricciones de base de datos cuando corresponda.

Esta fase es excelente para aprender:

- transacciones;
- concurrencia;
- race conditions;
- consistencia de datos.

## Pruebas

```text
✓ reservar con espacio
✓ impedir registro duplicado
✓ impedir reserva sin espacio
✓ impedir reserva de sesión cancelada
✓ estudiante puede cancelar su participación
```

Después agregar una prueba de concurrencia o una prueba de integración que intente simular reservas simultáneas.

---

# FASE 13 — Crear React

## Objetivo

Crear la interfaz independientemente del backend.

Desde la raíz:

```bash
npm create vite@latest frontend -- --template react
```

Después:

```bash
cd frontend
npm install
npm run dev
```

Por defecto Vite mostrará la URL local que corresponde al servidor de desarrollo, normalmente un puerto como `5173`.

## Qué aprender

Antes de conectar FastAPI, estudiar:

- JSX.
- Componentes.
- Props.
- Estado.
- Eventos.
- `useState`.
- `useEffect`.
- Formularios.
- Renderizado condicional.

## Primer ejercicio

Crear manualmente:

```text
<Header />
<LoginForm />
<AsesoriaCard />
```

No conectarlos todavía al backend.

## Prueba

`npm run dev`.

La interfaz debe abrir y no mostrar errores en la consola del navegador.

---

# FASE 14 — Estructura del frontend

Crear gradualmente:

```text
src/
├── components/
│   ├── common/
│   ├── forms/
│   └── layout/
├── pages/
├── services/
├── hooks/
├── context/
├── utils/
└── styles/
```

Ejemplo:

```text
pages/Login/LoginPage.jsx
pages/Dashboard/DashboardPage.jsx
pages/Asesorias/AsesoriasPage.jsx
```

## Separación recomendada

No colocar llamadas `fetch()` por toda la aplicación.

Centralizarlas:

```text
services/
├── api.js
├── authService.js
└── asesoriaService.js
```

Ejemplo conceptual:

```javascript
export async function obtenerAsesorias() {
  const response = await fetch(
    `${import.meta.env.VITE_API_URL}/api/asesorias`
  );

  if (!response.ok) {
    throw new Error("No fue posible cargar las asesorías");
  }

  return response.json();
}
```

---

# FASE 15 — Conectar React con FastAPI

Durante desarrollo:

```text
React
http://localhost:5173

FastAPI
http://localhost:8000
```

Como son orígenes distintos, FastAPI debe permitir explícitamente al frontend mediante CORS.

Ejemplo:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Para producción:

```python
allow_origins=[
    "https://app.institucion.edu.mx"
]
```

Evitar utilizar `"*"` indiscriminadamente en producción, especialmente si se manejan credenciales.

## Primera integración

Crear un endpoint:

```text
GET /api/health
```

Respuesta:

```json
{
  "status": "ok"
}
```

Desde React llamar:

```javascript
fetch("http://localhost:8000/api/health")
```

Mostrar:

```text
Backend conectado ✓
```

## Qué aprender

- CORS.
- HTTP.
- `fetch`.
- Promesas.
- `async/await`.
- Manejo de errores.
- Estados de carga.

## Pruebas

Probar tres situaciones:

```text
1. backend encendido
2. backend apagado
3. backend responde error
```

La interfaz debe manejar todas sin romperse.

---

# FASE 16 — Login desde React

## Flujo

```text
LoginPage
    ↓
authService.login()
    ↓
POST /api/auth/login
    ↓
FastAPI
    ↓
validación
    ↓
respuesta
    ↓
React actualiza sesión
```

Estados mínimos:

```text
loading
success
error
```

No mostrar errores internos como:

```text
sqlalchemy.exc...
Traceback...
```

Mostrar mensajes aptos para usuario.

---

# FASE 17 — Primera funcionalidad vertical completa

Antes de intentar completar todo SIAA, desarrollar una funcionalidad de principio a fin.

Recomendación:

## Consultar asesorías disponibles

Debe atravesar:

```text
PostgreSQL
   ↓
SQLAlchemy
   ↓
Repository
   ↓
Service
   ↓
FastAPI
   ↓
JSON
   ↓
Fetch
   ↓
React
   ↓
AsesoriaCard
```

Cuando puedan explicar cada flecha, ya estarán entendiendo la arquitectura.

## Prueba completa

1. Insertar asesorías de prueba.
2. Ejecutar backend.
3. Ejecutar frontend.
4. Abrir página.
5. Ver las asesorías.
6. Apagar backend.
7. Confirmar mensaje de error.
8. Volver a iniciar backend.
9. Confirmar recuperación.

---

# FASE 18 — Flujo completo de reservación

Implementar:

```text
Login estudiante
       ↓
buscar materia
       ↓
ver docentes/asesorías
       ↓
seleccionar asesoría
       ↓
reservar
       ↓
confirmación
       ↓
ver "Mis asesorías"
```

Esta debería convertirse en una de las primeras historias de usuario completas del MVP.

## Pruebas de aceptación

### Caso 1

```text
Dado un estudiante autenticado
Y una asesoría con lugares disponibles
Cuando selecciona reservar
Entonces queda registrado como participante
Y la asesoría aparece en "Mis asesorías"
```

### Caso 2

```text
Dada una asesoría sin cupos
Cuando un estudiante intenta reservar
Entonces el sistema rechaza la operación
Y muestra un mensaje apropiado
```

---

# FASE 19 — Validación del MVP

Antes de agregar foro, notificaciones o estadísticas, comprobar que funcionan bien estas funciones:

- Login.
- Roles.
- Catálogo de carreras.
- Catálogo de materias.
- Temas.
- Docentes.
- Disponibilidades.
- Creación de asesorías.
- Consulta de asesorías.
- Reservación.
- Cancelación.
- Cupos.
- Asesoría individual.
- Asesoría grupal.

Si estas funciones no son sólidas, agregar más módulos solamente aumentará la complejidad.

---

# FASE 20 — Calidad del código

Cuando el MVP funcione, comenzar refactorización controlada.

## Backend

Revisar:

- funciones muy grandes;
- lógica duplicada;
- rutas con lógica de negocio;
- consultas repetidas;
- manejo inconsistente de errores;
- nombres ambiguos.

## Frontend

Revisar:

- componentes demasiado grandes;
- `fetch` duplicados;
- estados duplicados;
- lógica de negocio dentro de componentes visuales;
- estilos difíciles de mantener.

## Herramientas

Agregar gradualmente herramientas de formato y análisis estático.

No es necesario instalar diez herramientas desde el primer día.

---

# FASE 21 — Pruebas necesarias antes de producción

Deben existir varias capas.

## 1. Pruebas unitarias

Prueban lógica aislada.

Ejemplo:

```text
calcular_cupo_disponible()
```

## 2. Pruebas de integración

Prueban varios componentes.

Ejemplo:

```text
FastAPI + PostgreSQL de pruebas
```

## 3. Pruebas de API

Ejemplo:

```text
POST /api/asesorias/{id}/reservar
```

## 4. Pruebas frontend

Componentes y flujos críticos.

## 5. Pruebas manuales exploratorias

Buscar situaciones no contempladas.

## 6. Pruebas de concurrencia

Especialmente:

- reservas;
- cupos;
- cancelaciones simultáneas.

---

# FASE 22 — Base de datos de pruebas

Nunca ejecutar automáticamente las pruebas sobre la base de producción.

Separar:

```text
siaa_dev
siaa_test
siaa_prod
```

Conceptualmente:

```text
DESARROLLO
FastAPI → siaa_dev

PRUEBAS
Pytest → siaa_test

PRODUCCIÓN
SIAA → siaa_prod
```

Las credenciales deben ser diferentes.

---

# FASE 23 — Docker

No recomiendo empezar el proyecto aprendiendo React, FastAPI, PostgreSQL y Docker simultáneamente.

Primero:

```text
React ✓
FastAPI ✓
PostgreSQL ✓
Integración ✓
```

Después introducir Docker.

La arquitectura será aproximadamente:

```text
docker compose
│
├── frontend
├── backend
└── postgres
```

## Qué aprender

- Imagen.
- Contenedor.
- Dockerfile.
- Volumen.
- Puerto.
- Red.
- Docker Compose.

## Prueba

En un equipo limpio:

```bash
docker compose up
```

y comprobar que el sistema arranca de manera reproducible.

---

# FASE 24 — Preparación para producción

Llegar a producción no consiste únicamente en ejecutar:

```bash
uvicorn app.main:app
```

Se deben revisar varias áreas.

## Configuración

Separar:

```text
development
testing
production
```

## Secretos

Nunca dentro del repositorio.

Ejemplos:

```text
DATABASE_URL
SECRET_KEY
credenciales de servicios externos
```

## Base de datos

- Usuario específico.
- Contraseña fuerte.
- Backups.
- Migraciones controladas.
- Restauración probada.
- Conexiones protegidas según infraestructura.

## Backend

- Configuración de producción.
- Logging.
- Manejo global de errores.
- Timeouts.
- Health checks.
- Límites apropiados.
- Validación estricta.

## Frontend

Crear build:

```bash
npm run build
```

Esto genera archivos optimizados para despliegue.

## HTTPS

Producción debe utilizar HTTPS.

Arquitectura frecuente:

```text
Internet
   ↓
HTTPS
   ↓
Proxy / Load Balancer
   ├── frontend
   └── FastAPI
           ↓
       PostgreSQL
```

## CORS

Permitir únicamente los dominios necesarios.

## Backups

Un backup que nunca se ha restaurado todavía no ha demostrado que sirve.

Periódicamente debe probarse el procedimiento de restauración.

---

# FASE 25 — Logging y observabilidad

Cuando algo falle en producción, se necesita saber qué pasó.

Registrar:

- endpoint;
- código HTTP;
- duración;
- errores;
- identificador de petición cuando sea posible.

No registrar:

- contraseñas;
- tokens completos;
- secretos;
- datos sensibles innecesarios.

Posteriormente se pueden agregar:

- métricas;
- alertas;
- monitorización de errores;
- monitorización de disponibilidad.

---

# FASE 26 — CI/CD

Cuando el proyecto ya cuente con pruebas estables, configurar un pipeline.

Ejemplo:

```text
push / pull request
       ↓
instalar backend
       ↓
ejecutar pytest
       ↓
instalar frontend
       ↓
ejecutar pruebas
       ↓
npm run build
       ↓
si todo pasa:
permitir despliegue
```

Una rama rota no debería llegar directamente a producción.

---

# FASE 27 — Estrategia Git

Una estrategia sencilla para aprender:

```text
main
│
├── develop
│
├── feature/login
├── feature/asesorias
├── feature/disponibilidad
└── fix/cupo-asesoria
```

Flujo:

```text
crear rama
    ↓
trabajar
    ↓
probar
    ↓
commit
    ↓
push
    ↓
Pull Request
    ↓
revisión
    ↓
merge
```

Ejemplos de commits:

```text
feat: add career creation endpoint
feat: implement student reservation
fix: prevent duplicate reservation
test: add reservation capacity tests
refactor: move booking rules to service layer
docs: document local setup
```

---

# 28. Orden recomendado de implementación

El orden general del proyecto puede ser:

```text
01. Configurar repositorio
02. FastAPI funcionando
03. PostgreSQL funcionando
04. SQLAlchemy conectado
05. Alembic configurado
06. Modelos básicos
07. CRUD de carreras
08. CRUD de materias
09. CRUD de temas
10. Usuarios
11. Autenticación
12. Roles y autorización
13. Docentes y estudiantes
14. Relaciones docente-materia
15. Relaciones docente-tema
16. Disponibilidades
17. Crear asesorías
18. Consultar asesorías
19. Reservar asesorías
20. Control de cupo
21. Cancelar participación
22. React
23. Layout y navegación
24. Login React
25. Consumo de API
26. Lista de asesorías
27. Reservación desde React
28. Mis asesorías
29. Dashboard docente
30. Pruebas completas
31. Docker
32. CI/CD
33. Staging
34. Seguridad
35. Producción
```

React aparece después de tener una API mínima deliberadamente.

Esto permite aprender primero qué está consumiendo el frontend.

Sin embargo, el diseño visual en Figma puede realizarse paralelamente.

---

# 29. Ciclo de trabajo recomendado para cada nueva característica

Supongamos:

> El estudiante puede cancelar una reservación.

Trabajar así:

## Paso 1 — Definir comportamiento

```text
¿Qué usuario?
¿Qué entrada?
¿Qué resultado?
¿Qué errores?
```

## Paso 2 — Diseñar datos

¿Necesita una tabla nueva?

¿Necesita modificar una existente?

## Paso 3 — Definir endpoint

```text
DELETE /api/asesorias/{id}/participacion
```

o la forma REST acordada por el equipo.

## Paso 4 — Implementar regla en service

No empezar por React.

## Paso 5 — Probar backend

```text
caso correcto
no autenticado
usuario incorrecto
asesoría inexistente
participación inexistente
```

## Paso 6 — Automatizar pruebas

Pytest.

## Paso 7 — Implementar interfaz

Botón:

```text
Cancelar reservación
```

## Paso 8 — Probar integración

React + API + base.

## Paso 9 — Revisar

Otro integrante revisa el cambio.

## Paso 10 — Merge

Solamente cuando pasa las pruebas.

Este ciclo puede repetirse para prácticamente todas las funcionalidades.

---

# 30. Qué NO hacer al inicio

Evitar:

- Microservicios.
- Kubernetes.
- Redux sin necesidad.
- Arquitecturas excesivamente complejas.
- Implementar todas las tablas en un día.
- Crear frontend y backend completos sin pruebas intermedias.
- Guardar contraseñas sin hash.
- Subir `.env`.
- Modificar directamente la base de producción.
- Utilizar la cuenta administrador de PostgreSQL como cuenta de aplicación en producción.
- Depender únicamente de validaciones del frontend.
- Copiar código que el equipo no pueda explicar.

La meta es evolucionar:

```text
simple
↓
correcto
↓
probado
↓
mantenible
↓
seguro
↓
escalable
```

y no intentar comenzar directamente por el último punto.

---

# 31. Definición de "terminado"

Una funcionalidad no está terminada solamente porque "funciona en mi computadora".

Una historia puede considerarse terminada cuando:

- Cumple el requisito.
- Tiene validaciones.
- Maneja errores.
- Respeta permisos.
- Tiene pruebas relevantes.
- No rompe pruebas anteriores.
- Se puede explicar.
- Está documentada cuando corresponde.
- Fue revisada.
- Puede desplegarse de manera reproducible.

---

# 32. Primer milestone recomendado

## Milestone 1 — Base técnica

Objetivo:

```text
React → FastAPI → PostgreSQL
```

Entregables:

- Repositorio.
- Backend FastAPI.
- PostgreSQL.
- SQLAlchemy.
- Alembic.
- Endpoint `/api/health`.
- React.
- React consume `/api/health`.
- README con instrucciones.
- Primera prueba automatizada.

Al terminar deben poder demostrar:

```text
React muestra:
"Servidor SIAA conectado"
```

obtenido realmente desde FastAPI.

---

# 33. Segundo milestone recomendado

## Milestone 2 — Catálogo académico

Implementar:

- carreras;
- materias;
- temas;
- docentes;
- docente-materia;
- docente-tema.

Demostración:

```text
Administrador crea materia
      ↓
crea temas
      ↓
asigna docente
      ↓
React muestra información
```

---

# 34. Tercer milestone recomendado

## Milestone 3 — Seguridad y perfiles

Implementar:

- usuarios;
- login;
- JWT o mecanismo seleccionado;
- estudiante;
- docente;
- roles;
- autorización.

Demostración:

```text
Estudiante inicia sesión
Docente inicia sesión
Ambos reciben interfaces y permisos diferentes
```

---

# 35. Cuarto milestone recomendado

## Milestone 4 — Disponibilidad y asesorías

Implementar:

- disponibilidad;
- creación de asesoría;
- búsqueda;
- filtros.

Demostración:

```text
Docente:
define disponibilidad
        ↓
crea asesoría

Estudiante:
consulta asesoría
```

---

# 36. Quinto milestone recomendado

## Milestone 5 — Reservaciones

Implementar:

- participantes;
- reservar;
- cancelar;
- cupos;
- individual;
- grupal;
- historial.

Esta fase representa el núcleo funcional del MVP.

---

# 37. Sexto milestone recomendado

## Milestone 6 — Robustez

Implementar:

- pruebas completas;
- control de concurrencia;
- logging;
- manejo global de errores;
- Docker;
- CI;
- base de staging;
- backups;
- seguridad;
- documentación.

Solamente después se recomienda preparar producción.

---

# 38. Ambientes

Antes de producción disponer de al menos:

```text
LOCAL / DEVELOPMENT
        ↓
TEST
        ↓
STAGING
        ↓
PRODUCTION
```

## Development

Donde programamos.

## Test

Donde ejecutamos pruebas automatizadas.

## Staging

Debe parecerse a producción y permite realizar pruebas finales.

## Production

Usuarios reales y datos reales.

No utilizar producción como ambiente de pruebas.

---

# 39. Checklist previa a producción

## Aplicación

- [ ] No hay secretos en Git.
- [ ] CORS está limitado.
- [ ] HTTPS está activo.
- [ ] Contraseñas almacenadas como hash.
- [ ] Tokens tienen expiración.
- [ ] Endpoints sensibles requieren permisos.
- [ ] Errores internos no llegan al usuario.
- [ ] Logging configurado.
- [ ] Health checks configurados.

## Base de datos

- [ ] Migraciones versionadas.
- [ ] Backups automáticos.
- [ ] Restauración probada.
- [ ] Usuario de aplicación con permisos mínimos necesarios.
- [ ] Índices revisados.
- [ ] Restricciones de integridad.
- [ ] Datos de prueba separados de producción.

## Pruebas

- [ ] Unitarias.
- [ ] Integración.
- [ ] API.
- [ ] Flujos críticos.
- [ ] Reservas concurrentes.
- [ ] Autorización por rol.

## Operación

- [ ] Dominio.
- [ ] TLS/HTTPS.
- [ ] Monitoreo.
- [ ] Alertas.
- [ ] Procedimiento de rollback.
- [ ] Procedimiento de backup.
- [ ] Procedimiento de restauración.

---

# 40. Forma recomendada de estudiar mientras construimos SIAA

Para cada tecnología responder cuatro preguntas.

## React

```text
¿Qué problema resuelve?
¿Qué hace un componente?
¿Qué es estado?
¿Cómo llama a FastAPI?
```

## FastAPI

```text
¿Qué es un endpoint?
¿Cómo valida Pydantic?
¿Cómo funcionan dependencias?
¿Cómo protegemos rutas?
```

## SQLAlchemy

```text
¿Qué representa un modelo?
¿Qué hace una Session?
¿Qué es una relación?
¿Cuándo ocurre commit/rollback?
```

## PostgreSQL

```text
¿Qué es PK?
¿Qué es FK?
¿Qué es UNIQUE?
¿Qué es una transacción?
¿Qué es un índice?
```

## Alembic

```text
¿Qué problema resuelve?
¿Qué es revision?
¿Qué es upgrade?
¿Por qué se revisa una migración?
```

## Git

```text
¿Qué es commit?
¿Qué es branch?
¿Qué es merge?
¿Qué es pull request?
```

El proyecto debe servir como laboratorio para responder esas preguntas con código real.

---

# 41. Documentación mínima del repositorio

Mantener:

```text
README.md
docs/
├── arquitectura.md
├── der.md
├── api.md
└── decisiones.md
```

## `decisiones.md`

Registrar decisiones importantes.

Ejemplo:

```markdown
## ADR-001 — React como frontend

Decidimos utilizar React con Vite porque la aplicación tendrá
múltiples pantallas interactivas y queremos aprender separación
frontend/backend.

## ADR-002 — FastAPI como API

FastAPI será responsable de reglas de negocio, seguridad y acceso
a PostgreSQL.

## ADR-003 — Una tabla para asesorías individuales y grupales

Ambas se almacenan en `asesorias`; la cantidad de participantes
se controla mediante `participantes_asesoria`.
```

Esto ayuda a recordar por qué existe la arquitectura actual.

---

# 42. Comandos frecuentes

## Backend

Activar entorno virtual y ejecutar:

```bash
uvicorn app.main:app --reload
```

## Pruebas backend

```bash
pytest
```

## Migraciones

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
alembic history
```

## Frontend

```bash
npm install
npm run dev
```

## Build frontend

```bash
npm run build
```

## Git

```bash
git status
git add .
git commit -m "mensaje"
git push
```

---

# 43. Fuentes oficiales recomendadas

Utilizar preferentemente documentación oficial durante el desarrollo.

## React

https://react.dev/

La documentación oficial también explica la adopción gradual de React y actualmente desaconseja iniciar proyectos nuevos con Create React App.

## Vite

https://vite.dev/guide/

Vite proporciona servidor de desarrollo y generación de assets optimizados para producción.

## FastAPI

https://fastapi.tiangolo.com/

## SQLAlchemy

https://docs.sqlalchemy.org/

Para este proyecto estudiar especialmente:

- ORM Quick Start.
- Declarative Models.
- Relationships.
- Session.
- Transactions.

## Alembic

https://alembic.sqlalchemy.org/

## PostgreSQL

https://www.postgresql.org/docs/

Política de versiones:

https://www.postgresql.org/support/versioning/

En octubre de 2026 PostgreSQL mantiene soportadas las ramas 14, 15, 16, 17 y 18. Para un despliegue nuevo conviene elegir una rama oficialmente soportada, considerar el soporte disponible en el proveedor de infraestructura y mantener al día las versiones menores.

---

# 44. Principio final del proyecto

SIAA debe construirse en dos direcciones simultáneamente:

```text
Aprender                    Construir bien
   │                              │
   ├─ entender HTTP               ├─ API clara
   ├─ entender SQL                ├─ integridad de datos
   ├─ entender React              ├─ interfaz mantenible
   ├─ entender seguridad          ├─ autenticación segura
   └─ entender pruebas            └─ sistema confiable
                  \              /
                   \            /
                    ▼          ▼
                       SIAA
```

La prioridad no debe ser terminar la mayor cantidad de pantallas posible.

La prioridad debe ser que cada nueva función tenga una arquitectura que el equipo comprenda y pueda mantener.

Una buena secuencia es:

```text
entender
→ diseñar
→ implementar
→ probar
→ explicar
→ documentar
→ mejorar
```

Cuando ese ciclo se repite durante todo el proyecto, SIAA deja de ser únicamente una tarea universitaria y se convierte en una aplicación con bases reales para evolucionar hacia producción.
