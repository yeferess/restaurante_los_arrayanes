#constitution.md
Vamos a crear la constitución de un proyecto nuevo: un sistema de pedidos para
un restaurante de un solo local, compuesto por un backend en Django (API REST
+ Django Channels) y dos frontends en Next.js (panel de administración y PWA
para meseros), con base de datos SQLite, pensado para operar 100% en la red
WiFi local del restaurante, sin depender de internet para funcionar.

Proponme un docs/constitution.md con principios innegociables, cortos y
verificables, que cubran:
- simplicidad del stack (Django + Next.js + SQLite, sin infraestructura
  innecesaria como Redis, microservicios o Postgres)
- operación offline-first en red local (nada crítico depende de internet)
- separación clara entre backend y frontend (contrato de API)
- trazabilidad: ninguna acción sensible (anulación, cobro, cambio de mesa)
  se ejecuta sin registrar quién, cuándo y por qué
- permisos por rol (qué puede hacer un mesero vs. un admin)
- política de tests
- idioma del código y los mensajes de commit

Máximo 15 líneas. Espera mi aprobación antes de darlo por definitivo.

#AGENTS.md y CLAUDE.md
Ahora vamos a crear el AGENTS.md del proyecto: instrucciones para cualquier
agente de código que trabaje aquí (Claude Code, Copilot, etc.).

Estructura del monorepo:
- /backend        → Django + DRF + Django Channels + SQLite
- /frontend       → Next.js (un solo proyecto: rutas para el panel de admin
                     y rutas para la PWA del mesero)
- /docs           → docs/constitution.md
- /specs          → especificaciones por funcionalidad (spec-driven development)

Genera un AGENTS.md (máximo una página) que incluya:
- descripción breve del proyecto
- la estructura de carpetas de arriba
- cómo instalar dependencias y levantar el backend y el frontend en local
- cómo correr los tests de cada parte
- convenciones de nombres y de mensajes de commit
- una referencia obligatoria: "toda tarea debe respetar docs/constitution.md"

Cuando termines, crea también un archivo CLAUDE.md en la raíz que contenga
únicamente esta línea: @AGENTS.md


#Spec
#especificacion autenticacion

NO escribas código en ningún momento. Lee docs/constitution.md. Vamos a
redactar la especificación de la primera funcionalidad del sistema:
autenticación y gestión de usuarios.

Contexto ya decidido (no lo cuestiones, ya está definido):
- Hay dos roles: admin y mesero.
- El admin crea las cuentas de los meseros (usuario + contraseña) desde el
  panel de escritorio.
- El admin puede restablecer la contraseña de un mesero, pero NO puede editar
  ningún otro dato del mesero una vez creado (para no poder manipular la
  trazabilidad). Si un mesero deja de trabajar o hay un error, se desactiva
  la cuenta, nunca se edita ni se borra su historial.
- Hay dos puntos de entrada separados a la misma aplicación Next.js: /admin
  (panel del administrador) y /mesero (PWA del mesero). Cada uno lleva
  directo al login de su rol, sin pantalla compartida de selección de rol.
- El cobro/liquidación de mesas es exclusivo del rol admin (relevante para
  definir permisos, aunque el cobro en sí se especifique en otro módulo).

Tu trabajo:
1. Hazme preguntas de UNA en UNA para eliminar ambigüedades sobre este módulo
   específico (ej. política de contraseñas, qué pasa tras varios intentos
   fallidos, duración de la sesión, qué pasa si se desactiva un mesero con
   una mesa abierta, si existe un admin por defecto al instalar el sistema,
   qué queda fuera del MVP). Máximo 6 preguntas.
2. Con mis respuestas, genera specs/001-autenticacion-usuarios/spec.md con
   esta estructura: contexto y objetivo, usuarios, historias de usuario,
   requisitos funcionales numerados (RF-x) con criterios de aceptación en
   notación EARS en español, requisitos no funcionales, casos límite, fuera
   de alcance, criterios de finalización, y dudas abiertas marcadas como
   [NECESITA ACLARACIÓN].
3. Solo el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de
   archivo — eso va en el plan.


# clarificacion
Revisa specs/001-autenticacion-usuarios/spec.md como si fueras un QA muy
profesional. Lista:
1. Ambigüedades restantes.
2. Contradicciones entre requisitos.
3. Casos límite no cubiertos.
4. Conflictos con docs/constitution.md.

No propongas soluciones todavía: solo detecta. Formato: lista numerada.

# plan.md
Lee docs/constitution.md y specs/001-autenticacion-usuarios/spec.md. NO
escribas código todavía.

Genera specs/001-autenticacion-usuarios/plan.md con:

1. Estructura de módulos/archivos: cómo se organiza esto dentro de /backend
   (apps de Django, modelos, vistas, serializers) y de /frontend (rutas
   /admin y /mesero relacionadas con login).
2. Modelo de datos: tabla(s) de Usuario con sus campos, tipos y
   restricciones, con un ejemplo de registro para admin y otro para mesero.
3. Contrato de la API: cada endpoint necesario (login admin, login mesero,
   crear mesero, restablecer PIN, activar/desactivar mesero, desbloquear
   cuenta, crear admin adicional, cambiar contraseña propia de admin),
   método HTTP, qué recibe, qué responde, y los códigos de error para cada
   caso cubierto en los RF (intentos fallidos, bloqueo, inactividad de 30
   minutos, etc.).
4. Pseudocódigo del algoritmo de bloqueo por intentos fallidos y del
   control de inactividad/sesión (incluyendo el "heartbeat" de actividad
   del admin).
5. Decisiones técnicas justificadas: para cada una, indica también la
   alternativa que descartaste y por qué (ej. JWT vs. sesión de Django,
   cómo se hashea el PIN vs. la contraseña).
6. Estrategia de tests: qué se cubre con tests unitarios y qué con tests
   de integración.

Todo debe respetar docs/constitution.md y cubrir el 100% de los RF de la
spec. Marca explícitamente qué RF cubre cada parte del plan.

#task.md
A partir de specs/001-autenticacion-usuarios/spec.md y
specs/001-autenticacion-usuarios/plan.md, genera
specs/001-autenticacion-usuarios/tasks.md: tareas pequeñas (máx. 20-30 min
cada una), en orden de dependencia, cada una con los RF que cubre y una
línea "Hecho cuando:" verificable. Usa checkboxes.

#implementacion
Implementa SOLO la tarea T2 de specs/001-autenticacion-usuarios/tasks.md,
siguiendo plan.md y docs/constitution.md. Escribe primero los tests, luego
el código.

Ejecuta la suite de tests del backend (la que hayas definido en plan.md)
y muéstrame el resultado.

Al terminar: marca T2 como hecha en tasks.md, indica qué RF cubre, y
PÁRATE. No empieces T3.

#implementacion de todos los task
Vamos a implementar specs/001-autenticacion-usuarios/tasks.md completa,
pero SIEMPRE una tarea a la vez, respetando plan.md y docs/constitution.md.

Para cada tarea pendiente, en este orden:
1. Escribe primero los tests, luego el código.
2. Ejecuta la suite de tests del backend y muéstrame el resultado.
3. Marca la tarea como hecha en tasks.md e indica qué RF cubre.
4. PÁRATE y espera mi confirmación explícita antes de empezar la siguiente
   tarea. Nunca implementes dos tareas seguidas sin que yo te lo pida.

Empieza por la primera tarea pendiente.

#automaticas por fases:
Vamos a implementar specs/001-autenticacion-usuarios/tasks.md completa,
pero SIEMPRE una tarea a la vez, respetando plan.md y docs/constitution.md.

Para cada tarea pendiente, en este orden:
1. Escribe primero los tests, luego el código.
2. Ejecuta la suite de tests del backend y muéstrame el resultado.
3. Marca la tarea como hecha en tasks.md e indica qué RF cubre.
4. Si alguna tarea falla sus tests, DETENTE de inmediato ahí mismo — no
   continúes con las siguientes tareas de la fase aunque falten para
   llegar a T18.
5. Si la tarea pasa, continúa directo con la siguiente de la fase, sin
   pedirme confirmación tarea por tarea.

PÁRATE solo al llegar a T18 (o antes, si algo falla) y espera mi
confirmación explícita antes de empezar la siguiente fase de tareas.

Empieza por la primera tarea pendiente: T10. Esta fase va hasta la T18.

################################
#segunda spec Menu

NO escribas código en ningún momento. Lee docs/constitution.md. Vamos a
redactar la especificación de la segunda funcionalidad del sistema:
gestión del menú (catálogo de productos).

Contexto ya decidido (no lo cuestiones):
- Los productos del menú los crea, edita y desactiva únicamente el admin,
  desde el panel /admin.
- Cada producto tiene: nombre, categoría, precio, disponibilidad (sí/no).
- Los cambios de menú se propagan en tiempo real a las apps de los meseros
  (vía Django Channels/WebSocket); además debe existir un botón manual de
  "Actualizar menú" en la app del mesero como respaldo si no llega el
  evento en tiempo real.
- El mesero solo puede leer el menú, nunca editarlo.
- Este módulo depende de 001-autenticacion-usuarios (ya implementado): los
  endpoints de menú requieren sesión autenticada y verifican el rol.

Tu trabajo:
1. Hazme preguntas de UNA en UNA para eliminar ambigüedades sobre este
   módulo específico (ej. ¿se pueden eliminar productos definitivamente o
   solo desactivar? ¿hay categorías predefinidas o libres? ¿qué pasa si se
   desactiva un producto que está en un pedido ya abierto? ¿el cambio de
   precio de un producto afecta pedidos ya abiertos con ese producto, o
   solo pedidos nuevos? ¿lleva imagen el producto? ¿qué pasa si dos admins
   editan el mismo producto al mismo tiempo?). Máximo 6 preguntas.
2. Con mis respuestas, genera specs/002-gestion-menu/spec.md con la misma
   estructura que la spec anterior: contexto y objetivo, usuarios,
   historias de usuario, requisitos funcionales numerados (RF-x) con
   criterios de aceptación EARS en español, requisitos no funcionales,
   casos límite, fuera de alcance, criterios de finalización, y dudas
   abiertas marcadas como [NECESITA ACLARACIÓN].
3. Solo el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de
   archivo — eso va en el plan.

#QA

#plan.md
Lee docs/constitution.md y specs/002-gestion-menu/spec.md. NO escribas
código todavía.

Genera specs/002-gestion-menu/plan.md con:

1. Estructura de módulos/archivos: cómo se organiza esto dentro de /backend
   (app de Django, modelos, vistas, serializers, consumers de Channels) y
   de /frontend (pantallas de /admin para gestionar categorías y
   productos, y la vista de menú de solo lectura en /mesero).
2. Modelo de datos: tabla Categoría (id, nombre) y tabla Producto
   (id, nombre, categoría_id, precio, disponible, activo), con un ejemplo
   de cada una.
3. Contrato de la API: cada endpoint necesario (crear/editar/desactivar
   categoría, crear/editar/desactivar producto, listar menú), método HTTP,
   qué recibe, qué responde, y los códigos de error para cada caso cubierto
   en los RF (incluyendo el intento de desactivar una categoría con
   productos activos asignados).
4. Mecanismo de propagación en tiempo real: cómo Django Channels notifica
   a las apps de los meseros cuando cambia el menú, y cómo funciona el
   botón manual de "Actualizar menú" como respaldo si no llega el evento.
5. Decisiones técnicas justificadas: para cada una, indica también la
   alternativa que descartaste y por qué.
6. Estrategia de tests: qué se cubre con tests unitarios y qué con tests
   de integración (incluyendo la notificación en tiempo real).

Todo debe respetar docs/constitution.md y cubrir el 100% de los RF de la
spec. Marca explícitamente qué RF cubre cada parte del plan.