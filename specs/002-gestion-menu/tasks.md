# 002 · Gestión del menú (catálogo de productos) — Tareas

Basado en `spec.md` (requisitos) y `plan.md` (diseño técnico). Cada tarea
es de ~20-30 min, están en orden de dependencia (no empezar una tarea sin
que las anteriores estén hechas). Cada una indica el/los RF que cubre y una
condición verificable de "Hecho cuando".

---

## Fase 0 — Setup del módulo

- [x] **T01 — Crear la app `menu`**
  RF: — (infraestructura)
  Hecho cuando: existe `apps/menu/` con la estructura de `plan.md`
  (sección 1), está en `INSTALLED_APPS`, y `python manage.py check` no
  reporta errores.

- [x] **T02 — Registrar `urls.py` del módulo**
  RF: — (infraestructura)
  Hecho cuando: `config/urls.py` incluye `apps.menu.urls` bajo `/api/menu/`
  y `/api/`, y una request a una ruta aún no implementada devuelve 404 (no
  500 ni error de importación).

---

## Fase 1 — Modelo de datos

- [x] **T03 — Modelo `Category`**
  RF: RF-1
  Hecho cuando: existe el modelo con `name` (`CharField(50)`) y
  `normalized_name` (`CharField(50)`, `unique=True`, recalculado a
  `name.lower()` en `save()`), y la migración aplica sin errores.

- [x] **T04 — Modelo `Product`**
  RF: RF-2, RF-3, RF-4, NFR precisión monetaria
  Hecho cuando: existe el modelo con `name`, `normalized_name`
  (`unique=True`), `category` (`ForeignKey(Category, on_delete=PROTECT)`),
  `price` (`DecimalField(max_digits=10, decimal_places=2)`) y
  `is_available` (`BooleanField`, default `True`); la migración aplica
  sin errores, y un intento manual (shell de Django) de borrar una
  `Category` con un `Product` asignado lanza `ProtectedError`.

---

## Fase 2 — Servicios de negocio (`services.py`)

- [x] **T05 — Unicidad case-insensitive de categoría**
  RF: RF-1
  Hecho cuando: crear o renombrar una categoría a un nombre que ya existe
  (ignorando mayúsculas/minúsculas) es rechazado por el servicio, incluso
  si la capitalización es distinta.

- [x] **T06 — Validación de nombre de categoría**
  RF: RF-1
  Hecho cuando: un nombre vacío o de más de 50 caracteres es rechazado
  tanto al crear como al renombrar.

- [x] **T07 — Regla "no eliminar categoría con productos asignados"**
  RF: RF-1
  Hecho cuando: eliminar una categoría con al menos un `Product` asignado
  es rechazado por el servicio (antes de tocar la base, sin depender solo
  del `PROTECT` de T04); eliminar una sin productos asignados sí procede.

- [x] **T08 — Unicidad case-insensitive de producto**
  RF: RF-2, RF-3
  Hecho cuando: crear un producto, o renombrar uno existente, a un nombre
  que ya existe en el catálogo (ignorando mayúsculas/minúsculas) es
  rechazado por el servicio.

- [x] **T09 — Validaciones de creación de producto**
  RF: RF-2
  Hecho cuando: nombre vacío o >100 caracteres, precio ≤0 o no numérico, y
  `category_id` inexistente son todos rechazados por el servicio.

- [x] **T10 — Rechazo de creación sin ninguna categoría existente**
  RF: RF-2
  Hecho cuando: con cero categorías en la base, cualquier intento de
  crear un producto es rechazado indicando que debe existir al menos una
  categoría primero.

- [x] **T11 — Servicio de disponibilidad (`is_available`)**
  RF: RF-4
  Hecho cuando: el servicio permite alternar `is_available` en ambos
  sentidos sin tocar ningún otro campo del producto (verificado en shell
  de Django, ya que el módulo de pedidos aún no existe).

- [x] **T12 — Servicio de eliminación definitiva de producto**
  RF: RF-5
  Hecho cuando: eliminar un producto borra la fila (`DELETE` real, no
  soft-delete) y no requiere ninguna comprobación de historial previo.

- [x] **T13 — `notificar_cambio_de_menu()` (stub) e integración en los
  servicios de escritura**
  RF: RF-6
  Hecho cuando: la función existe (aunque todavía no publique en
  Channels — eso es la Fase 4) y se llama exactamente desde crear/editar/
  cambiar disponibilidad/eliminar producto y desde renombrar categoría; un
  test manual confirma que **no** se llama al crear ni al eliminar una
  categoría sin productos asignados.

---

## Fase 3 — Endpoints de la API

- [x] **T14 — Reutilizar `IsAdmin`/`IsMesero` en `apps/menu`**
  RF: RF-8
  Hecho cuando: `apps/menu/permissions.py` importa las clases de
  `apps.accounts.permissions` (sin duplicar lógica), y un request de
  prueba sin sesión devuelve 401 en cualquier vista que las use.

- [x] **T15 — `GET` y `POST /api/menu/categorias`**
  RF: RF-1
  Hecho cuando: `GET` devuelve `[{id, name}]` para un admin autenticado
  (403 para mesero, 401 sin sesión); `POST` crea la categoría (201) o
  devuelve 400/409 según T05/T06.

- [x] **T16 — `PATCH /api/menu/categorias/{id}`**
  RF: RF-1
  Hecho cuando: renombra la categoría (200) aplicando T05/T06; sobre un
  `id` inexistente devuelve 404.

- [x] **T17 — `DELETE /api/menu/categorias/{id}`**
  RF: RF-1
  Hecho cuando: elimina (204) una categoría sin productos asignados;
  devuelve 409 si tiene al menos uno (T07); 404 si no existe.

- [x] **T18 — `GET` y `POST /api/menu/productos`**
  RF: RF-2
  Hecho cuando: `GET` devuelve la lista completa (incluidos no
  disponibles) solo para admin (403 mesero); `POST` crea el producto
  (201) aplicando T08/T09/T10, con disponibilidad `True` por defecto si
  no se especifica.

- [x] **T19 — `PATCH /api/menu/productos/{id}`**
  RF: RF-3
  Hecho cuando: edita nombre/categoría/precio (200) aplicando las mismas
  validaciones de T08/T09; 404 si el producto o la nueva categoría no
  existen; 409 si el nuevo nombre ya existe en otro producto.

- [x] **T20 — `POST /api/menu/productos/{id}/disponibilidad`**
  RF: RF-4
  Hecho cuando: cambia `is_available` (200) en ambos sentidos; 400 si
  falta el campo `is_available`; 404 si el producto no existe.

- [x] **T21 — `DELETE /api/menu/productos/{id}`**
  RF: RF-5
  Hecho cuando: elimina el producto (204) sin importar su estado; 404 si
  no existe.

- [x] **T22 — `GET /api/menu` (lectura del mesero)**
  RF: RF-7
  Hecho cuando: devuelve solo productos con `is_available=True` junto con
  su categoría, para admin o mesero autenticados; 401 sin sesión.

---

## Fase 4 — Propagación en tiempo real (Channels)

- [x] **T23 — `MenuConsumer`**
  RF: RF-6, RF-8
  Hecho cuando: un `WebsocketCommunicator` con sesión válida (admin o
  mesero) conecta y queda unido al grupo `"menu"`; uno sin sesión válida
  es rechazado al conectar.

- [x] **T24 — `routing.py` + wiring en `config/asgi.py`**
  RF: RF-6 (infraestructura)
  Hecho cuando: `/ws/menu/` resuelve al `MenuConsumer` a través del
  `ProtocolTypeRouter` del proyecto, sin romper las rutas HTTP existentes.

- [x] **T25 — Conectar `notificar_cambio_de_menu()` con `group_send` real**
  RF: RF-6
  Hecho cuando: un cliente conectado a `/ws/menu/` recibe el evento
  `{"type": "menu.actualizado"}` al crear/editar/cambiar disponibilidad/
  eliminar un producto, o al renombrar una categoría; no recibe nada al
  crear o eliminar una categoría sin productos asignados (T13).

---

## Fase 5 — Tests

- [x] **T26 — Unit tests de categoría (T05, T06, T07)**
  RF: RF-1
  Hecho cuando: cubren unicidad case-insensitive, validación de longitud/
  vacío, y el rechazo de eliminar con productos asignados; todos pasan.

- [x] **T27 — Unit tests de producto (T08, T09, T10)**
  RF: RF-2, RF-3
  Hecho cuando: cubren unicidad case-insensitive (crear y editar),
  validación de nombre/precio/categoría, y el rechazo de creación sin
  ninguna categoría existente; todos pasan.

- [x] **T28 — Unit tests de disponibilidad y lectura filtrada (T11)**
  RF: RF-4, RF-7
  Hecho cuando: confirman que alternar `is_available` no toca otros
  campos, y que la función de lectura de mesero excluye productos no
  disponibles; todos pasan.

- [x] **T29 — Unit tests de disparo de notificación (T13)**
  RF: RF-6
  Hecho cuando: confirman que `notificar_cambio_de_menu()` se llama en
  cada operación esperada y no se llama en crear/eliminar categoría
  vacía; todos pasan.

- [x] **T30 — Integration tests de endpoints de categorías (T15-T17)**
  RF: RF-1
  Hecho cuando: cada código de respuesta (200/201/204/400/401/403/404/
  409) de esos tres endpoints tiene al menos un test, y todos pasan.

- [x] **T31 — Integration tests de endpoints de productos (T18-T21)**
  RF: RF-2, RF-3, RF-4, RF-5
  Hecho cuando: cada código de respuesta de esos cuatro endpoints tiene
  al menos un test, y todos pasan.

- [x] **T32 — Integration test: flujo completo categoría→producto→
  eliminación**
  RF: RF-1, RF-2, RF-5
  Hecho cuando: un test end-to-end reproduce crear categoría → crear
  producto en ella → intentar eliminar la categoría (409) → eliminar el
  producto → eliminar la categoría (204).

- [x] **T33 — Integration tests de permisos y autenticación (RF-8)**
  RF: RF-8
  Hecho cuando: cada endpoint de la Fase 3 tiene un test que confirma 403
  para un mesero autenticado (en los de escritura y en las listas de
  gestión) y 401 sin sesión.

- [x] **T34 — Integration test: `GET /api/menu` excluye no disponibles**
  RF: RF-4, RF-7
  Hecho cuando: con productos disponibles y no disponibles en la base,
  la respuesta de `GET /api/menu` solo incluye los disponibles, mientras
  `GET /api/menu/productos` (admin) los incluye todos.

- [x] **T35 — Tests del canal en tiempo real (T23, T25)**
  RF: RF-6, RF-8
  Hecho cuando: cubren conexión con/sin sesión válida, recepción del
  evento en cada operación de T25, y la ausencia de evento en el caso
  límite de categoría vacía; todos pasan.

---

## Fase 6 — Frontend

- [x] **T36 — `lib/api/menu.ts`**
  RF: RF-1, RF-2, RF-3, RF-4, RF-5, RF-7
  Hecho cuando: expone una función por cada endpoint de la Fase 3,
  propagando los errores tal cual los devuelve la API.

- [x] **T37 — `lib/api/menuSocket.ts`**
  RF: RF-6
  Hecho cuando: abre `/ws/menu/`, reconecta con backoff ante
  desconexión, y expone un callback que se dispara al recibir
  `menu.actualizado`.

- [x] **T38 — Pantalla `admin/menu/categorias`**
  RF: RF-1
  Hecho cuando: permite crear, renombrar y eliminar categorías desde el
  panel, reflejando los errores 400/409 de T15-T17 en la UI.

- [x] **T39 — Pantalla `admin/menu/productos`**
  RF: RF-2, RF-3, RF-4, RF-5
  Hecho cuando: permite crear, editar, cambiar disponibilidad y eliminar
  productos; la categoría se selecciona siempre de una lista desplegable
  (nunca texto libre), poblada desde `GET /api/menu/categorias`.

- [x] **T40 — Pantalla `mesero/menu`**
  RF: RF-6, RF-7
  Hecho cuando: muestra el menú vigente (solo disponibles) vía
  `GET /api/menu`, se suscribe a `menuSocket.ts` para refrescarse sola
  ante cambios, y tiene un botón "Actualizar menú" que dispara el mismo
  refetch manualmente.

- [x] **T41 — Barra de búsqueda en los menús**
  RF: RF-9
  Hecho cuando: `lib/search.ts` compara sin mayúsculas ni tildes y
  devuelve la posición a resaltar; `MenuSearchBar` + `useMenuSearch` en
  `MenuMeseroView` y `ProductosManagement` resaltan, desplazan y cuentan
  coincidencias. Tests en `search.test.ts`, `MenuMeseroView.test.tsx` y
  `ProductosManagement.test.tsx`.
