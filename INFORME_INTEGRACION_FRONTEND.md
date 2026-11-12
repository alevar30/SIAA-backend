# Informe de integración del frontend SIAA

Fecha: 30 de octubre de 2026.

## Resultado

Se creó la aplicación en la carpeta existente `SIAA-frontend`, que estaba vacía y es
vecina de `SIAA-backend`. Se conservó la identidad azul/vino del archivo de Figma y se
implementaron las funciones de cuentas que soporta el backend, con las consultas
administrativas adicionales necesarias para formularios y listados.

La compatibilidad verificada corresponde a esas operaciones reales. El sistema de
asesorías completo todavía necesita sus modelos y endpoints antes de conectar todas
las pantallas del diseño. No se afirma que todo el MVP esté terminado.

## Funciones disponibles

- Login con correo, matrícula o número de empleado.
- Restauración del usuario y rol mediante `/auth/me`.
- Redirección obligatoria al cambio de contraseña temporal, incluso al abrir otra URL.
- Nuevo login después de cambiar contraseña, acorde con la revocación del backend.
- Cambio de contraseña desde la sección Seguridad y consulta del perfil propio.
- Navegación distinta para administración, estudiantes y docentes.
- Resumen administrativo con datos reales de cuentas y carreras.
- Usuarios por rol, búsqueda literal, paginación y consulta de perfiles.
- Altas de estudiante y docente con los nombres y formatos exactos de los schemas.
- Selección de carreras activas, semestre opcional y departamento opcional.
- Registro de carreras y manejo de duplicados.
- Contraseña temporal oculta inicialmente, con opción de mostrar y copiar. No se guarda
  en almacenamiento del navegador y desaparece al salir del recibo.
- Estados vacíos, errores por campo, conflictos, desconexión y reintento de sesión.

## Mejoras del diseño implementadas

- Layout con CSS Grid/Flex, componentes reutilizables y tokens compartidos.
- Desktop, tablet y móvil, con menú móvil modal y tarjetas de usuarios en pantallas pequeñas.
- Controles de al menos 44 px en las interacciones principales.
- Inputs con etiquetas, mensajes asociados y foco visible.
- Modales nativos con confinamiento de foco y cierre por teclado.
- Mejora del contraste de textos secundarios y nombres accesibles de navegación/secciones.
- Recursos SVG originales de Figma y fuente Inter guardados localmente.
- Se retiraron del acceso las acciones que no tienen soporte actual: Google y sesión
  permanente. La ayuda explica cómo solicitar un restablecimiento a administración.
- Se construyó la pantalla de cambio obligatorio que faltaba en el diseño.
- Los indicadores de asesorías no se sustituyeron por números inventados; el inicio
  administrativo muestra únicamente conteos que se pueden consultar en la base.

El archivo de Figma se utilizó como referencia; no fue modificado. Las mejoras están
implementadas en React. Las capturas de referencia están en `SIAA-frontend/docs/previews`.

## Cambios de backend para completar la integración

Se añadieron cuatro operaciones, todas protegidas por `require_admin`:

| Ruta | Finalidad |
|---|---|
| `GET /api/v1/admin/usuarios` | Listado paginado con rol, búsqueda e información del perfil |
| `GET /api/v1/admin/carreras` | Selector de carreras activas y catálogo administrativo |
| `POST /api/v1/admin/carreras` | Preparar carreras desde la interfaz |
| `GET /api/v1/admin/resumen` | Conteos reales para el inicio administrativo |

Las respuestas de consulta no contienen hashes, tokens ni contraseñas. El alta de
carrera normaliza la clave, valida la entrada y maneja duplicados con rollback.
No se añadieron tablas ni otra migración para estas consultas. La migración anterior
`20261030_01` sigue siendo necesaria para las sesiones versionadas.

## Verificación

- **Backend: 82 pruebas aprobadas y 1 omitida.** La omitida necesita PostgreSQL real.
- **Frontend: 19 pruebas aprobadas** de contratos HTTP, errores, bytes UTF-8, validaciones
  y protección de una sesión nueva frente a respuestas tardías de una anterior.
- **Navegador: 6 pruebas aprobadas en Chrome**, contra FastAPI y una base SQLite aislada.
- TypeScript y `npm run build`: aprobados.
- Formato Prettier, revisión Ruff y `git diff --check` del backend: aprobados.
- Chequeos axe de login desktop/móvil, usuarios móvil y formulario de alta: sin violaciones
  detectadas. Se revisaron capturas desktop y móvil. Esto no equivale a una certificación
  integral de accesibilidad ni a pruebas con todos los lectores de pantalla.

Los recorridos en navegador verificaron:

1. Login incorrecto/correcto, restauración al recargar, restricción de rutas y logout.
2. Alta de carrera y estudiante → entrega de contraseña temporal → cambio obligatorio
   con validación de confirmación → nuevo login con la contraseña personal.
3. Alta de docente, búsqueda por empleado y conflicto de correo existente.
4. Recuperación tras fallar la consulta de sesión por desconexión.
5. Eliminación de sesión al recibir un token inválido.
6. Menú móvil, ausencia de overflow del documento y accesibilidad de pantallas principales.

El servidor de navegador exige `SIAA_E2E=1`, crea una base temporal aleatoria dentro de
la carpeta ignorada de pruebas y elimina esa base al cerrarse normalmente. No usó una
base de producción ni creó cuentas reales.

## Cómo revisar

1. Configurar PostgreSQL y `.env` del backend según su README.
2. Aplicar `alembic upgrade head` y crear el primer administrador si no existe.
3. Iniciar FastAPI en el puerto 8000.
4. Desde `SIAA-frontend`, ejecutar `npm ci` y `npm run dev`.
5. Abrir `http://127.0.0.1:5173` e iniciar sesión con una cuenta real propia.

Para revisar solo las pruebas automatizadas: `npm run test:e2e` arranca ambos servicios
con datos aislados. Requiere Chrome en Windows y el entorno Python del backend.
El README del frontend explica variables públicas, proxy y configuración de producción.

## Pendientes explícitos

- Configurar y verificar el entorno real de PostgreSQL: no había conexión local disponible.
- Implementar materias/temas y sus relaciones con carreras/docentes.
- Implementar disponibilidad, sesiones, participantes, cupos, reservas y cancelaciones.
- Implementar edición/desactivación de usuarios y política de gestión de administradores
  si se incorporan como acciones del producto. La interfaz actual solo ofrece las
  operaciones implementadas y autorizadas.
- Definir Google institucional, recuperación autoservicio y renovación de sesión si
  forman parte del alcance. Actualmente la recuperación se hace con administración.
- Configurar hosting, HTTPS y proxy de producción antes de publicar. No se desplegó.

No se hicieron commits. El backend conserva su repositorio Git existente y el frontend
está en la carpeta vecina; esta entrega no reorganizó los repositorios.
