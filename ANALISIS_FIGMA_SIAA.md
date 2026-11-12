# Análisis del diseño Figma de SIAA

Archivo: [SIAA — Login Institucional](https://www.figma.com/design/nxHgVanCCV7vpesWyLIRcM/SIAA?node-id=0-1).

## Dictamen

El diseño ofrece una base visual coherente para SIAA y permite entender las tareas de
estudiantes, docentes y administración. Está más avanzado que el backend en cobertura
funcional. Antes de implementarlo completo hay que cerrar los flujos de autenticación,
reservación y administración, elegir las versiones definitivas de algunas pantallas
y preparar los componentes para distintos tamaños de pantalla.

Se revisó la única página del archivo: 17 pantallas de escritorio y 2 bibliotecas.
Se inspeccionaron capturas, textos, tamaños, componentes, auto layout e interacciones.
La comparación del backend corresponde al código local posterior a las correcciones.
Esta revisión no certifica accesibilidad ni comportamiento real de una aplicación web.

## Aciertos

- Azul y vino con uso consistente; fondos claros, tarjetas y navegación reconocibles.
- Acceso común para los roles, con navegación diferente según sus tareas.
- Separación de disponibilidad recurrente, sesión grupal y reservación individual.
- Vista previa antes de publicar una sesión grupal.
- Cupo lleno, mensajes de validación y estado de docente sin materias contemplados.
- Buena regla de dominio en las pantallas recientes: administración asigna materias;
  el docente selecciona temas dentro de ellas; la búsqueda cruza materia y tema.
- Bibliotecas con estados de foco, error, éxito, carga, selección y deshabilitado.

## Hallazgos prioritarios

### 1. Completar el acceso antes de conectar el login

[Login](https://www.figma.com/design/nxHgVanCCV7vpesWyLIRcM/SIAA?node-id=2-2)

El diseño ofrece Google Institucional, recuperación de contraseña y Recordar sesión.
El backend actual no tiene OAuth de Google, recuperación autoservicio ni renovación de
sesiones. Sí permite restablecimiento mediante un comando local de administración.
El token expira por defecto a los 30 minutos: persistirlo en el navegador no extiende
su vigencia.

Propuesta para el primer alcance:

- Conectar el acceso por contraseña existente.
- Etiquetar el identificador como «Correo, matrícula o número de empleado», o definir
  explícitamente que la interfaz inicial solo ofrecerá correo.
- Acordar si el correo debe pertenecer a un dominio institucional: el backend valida
  formato, pero todavía no restringe dominios.
- Diseñar cambio obligatorio con contraseña actual, nueva, confirmación, requisitos,
  mensajes de error, éxito y retorno al login.
- Diseñar cuenta desactivada, sesión expirada y servicio no disponible.
- Ofrecer recuperación mediante soporte mientras no exista recuperación autoservicio.
- Decidir el alcance de Google y Recordar sesión antes de presentarlos como acciones.

### 2. Corregir un solapamiento que oculta una acción

[Inicio del estudiante](https://www.figma.com/design/nxHgVanCCV7vpesWyLIRcM/SIAA?node-id=13-2)

El botón Buscar está en x=824, y=107, con tamaño 120×42 dentro del contenido.
El calendario comienza en x=816, y=102, con tamaño 358×460, en el mismo contenedor.
El calendario cubre por completo el botón; la captura confirma que este no aparece.

Agrupar campo y botón en una fila de auto layout y reservar una columna aparte al
calendario. Revisar también el buscador duplicado de la barra superior: ambos deben
tener un propósito distinto o compartir una única entrada visible.

### 3. Preparar reutilización y responsive reales

Las 17 pantallas miden 1440×900. Hay una nota de responsive para login, pero no se
observaron pantallas de móvil o tablet.

Las bibliotecas contienen 24 componentes y 3 conjuntos de variantes. Sin embargo,
las pantallas inspeccionadas no contienen instancias de componentes ni contenedores
con auto layout. Tampoco se encontraron reacciones de prototipo en sus nodos.

Consecuencias: cambiar el botón original no actualiza sus copias; un nombre largo o
un mensaje de error puede alterar la composición; el recorrido entre pantallas aún
no se puede validar mediante un prototipo conectado.

Propuesta: convertir sidebar, navbar, campos, botones, tarjetas, tablas, alertas y
modales en piezas reutilizables; usar auto layout; diseñar una versión móvil de los
flujos esenciales y conectar login → inicio → búsqueda → reserva → mis asesorías.

### 4. Mejorar legibilidad y áreas de interacción

El archivo contiene numerosos textos de 9–12 px en las pantallas, incluidos datos de
tablas, etiquetas y detalles. Para contenido principal propondría una base de 14–16 px,
probada a escala real con nombres y textos largos.

El checkbox del login mide 18×18; el dibujo del ojo, 18×11; algunos horarios, 92×30;
varios botones tienen 42 px de alto. La propia biblioteca propone áreas mínimas de
44 px. El icono puede seguir siendo pequeño si su área clicable es mayor; esa área
necesita quedar definida para la implementación.

Revisar foco de teclado, etiquetas de los botones de icono, orden de tabulación y
contraste al construir React. No se efectuó una auditoría completa de contraste.

### 5. Completar resultados y excepciones de los flujos

Hay un estado de cupo lleno y un estado vacío de materias; son buenos precedentes.
Faltan diseños explícitos para:

- Búsqueda sin resultados, cargando y con error de conexión.
- Horario ocupado entre la consulta y la confirmación de una reserva.
- Reserva confirmada, reserva ya existente y cancelación confirmada.
- Detalle de asesoría con acciones y reglas de cancelación según rol.
- Guardado de disponibilidad: cambios pendientes, éxito y conflicto de horarios.
- Alta/edición de usuarios y presentación de la contraseña temporal al administrador.
- Listados grandes: paginación, búsqueda, orden y estados sin registros.

El panel de reservación individual muestra una fecha y horas, pero no queda explicado
cómo cambiar de fecha, cerrar el panel o recuperarse de un conflicto al confirmar.

### 6. Definir estados y versiones definitivas

Se usan Confirmada, Programada, Pendiente, Realizada y Cancelada. Conviene distinguir
el estado de la sesión del estado de la participación del estudiante. «Pendiente»
requiere definir quién aprueba y cuándo; si no hay aprobación, no debería introducirse
como un estado ambiguo.

Hay dos versiones de búsqueda y de materias/temas:

- [Búsqueda anterior](https://www.figma.com/design/nxHgVanCCV7vpesWyLIRcM/SIAA?node-id=13-170)
  muestra a Laura sin el tema Normalización entre sus etiquetas aunque ese tema esté filtrado.
- [Búsqueda por materia y tema](https://www.figma.com/design/nxHgVanCCV7vpesWyLIRcM/SIAA?node-id=25-286)
  hace explícito el cruce correcto y muestra ese tema en ambos resultados.
- La pantalla antigua de materias es informativa; la nueva permite al docente elegir
  los temas dentro de materias asignadas por administración.

Recomiendo marcar las versiones recientes como definitivas y archivar visualmente las
anteriores para que el desarrollo no mezcle reglas.

### 7. Separar notas de diseño de contenido para usuarios

Varias pantallas contienen referencias a «MVP», «DER», relaciones DOCENTE ↔ MATERIA y
funciones excluidas. Son notas útiles para el equipo, pero deberían quedar fuera de
los frames destinados a la interfaz final.

El gráfico mensual de administración también necesita valores, escala o tooltips y
un período definido. Las barras sin cifras no permiten interpretar cantidades con precisión.

## Correspondencia con el backend

| Funcionalidad del diseño | Estado actual | Trabajo necesario |
|---|---|---|
| Login por contraseña | API existente | Conectar formulario, errores y redirección por rol |
| Identidad y rol | `/api/v1/auth/me` existente | Restaurar sesión y navegación |
| Cambio obligatorio | API existente; pantalla ausente | Diseñar e implementar el flujo completo |
| Alta de estudiante/docente | POST existentes | Formularios, catálogos para selectores y entrega de contraseña temporal |
| Listar, editar y desactivar usuarios | No hay endpoints | Consultas paginadas y operaciones autorizadas |
| Administradores | Bootstrap local inicial | Definir gestión posterior y sus permisos si se incluye en el producto |
| Carreras, materias y temas | Modelos existentes | CRUD y relaciones académicas |
| Asignar materias a docentes | Sin relación/API | `docente_materia` y permisos administrativos |
| Elegir temas a asesorar | Sin relación/API | `docente_tema`, limitado a materias asignadas |
| Disponibilidad recurrente | Sin modelo/API | Horarios, excepciones y generación de espacios reservables |
| Asesorías y reservaciones | Sin modelos/API | Sesiones, participantes, cupos, conflictos y cancelación |
| Indicadores y actividad reciente | Sin endpoints | Definir métricas, períodos y consultas/eventos necesarios |
| Google y recuperación autoservicio | No implementados | Decidir alcance y diseñar flujos completos |

## Reglas del producto por cerrar

1. Al quitar una materia o tema a un docente, decidir qué sucede con sus asesorías futuras.
2. Al cambiar disponibilidad, definir qué sucede con las reservas ya confirmadas.
3. Definir días excepcionales, vacaciones, vigencia del horario y zona horaria institucional.
4. Para sesiones virtuales, definir dónde se introduce el enlace y quién puede verlo.
5. Definir anticipación mínima de reserva, plazo de cancelación y criterios de finalización.
6. Diferenciar capacidad total, inscritos y lugares restantes. «8/15 lugares» puede
   sustituirse por «8 inscritos · 7 disponibles» para evitar ambigüedad.
7. Definir qué cuentan «Asesorías registradas», «Estudiantes atendidos» y «Temas disponibles».

## Orden recomendado

1. Ajustar login, crear cambio obligatorio y estados de autenticación.
2. Corregir el botón oculto; definir componentes y una base responsive.
3. Completar altas/listados y catálogos académicos.
4. Implementar administración asigna materias → docente selecciona temas.
5. Implementar disponibilidad → búsqueda → reserva → mis asesorías, con errores y cancelación.
6. Añadir indicadores y actividad cuando existan datos y definiciones verificables.

Mantendría la identidad visual. La prioridad es completar el comportamiento y la
consistencia entre pantallas, contratos de API y reglas del dominio.
