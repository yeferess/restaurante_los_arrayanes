# 003 · Mesas y pedidos — Tareas

Basado en `spec.md` (requisitos) y `plan.md` (diseño técnico). Cada tarea
es de ~20-30 min, están en orden de dependencia (no empezar una tarea sin
que las anteriores estén hechas). Cada una indica el/los RF que cubre y una
condición verificable de "Hecho cuando".

---

## Fase 0 — Setup del módulo

- [x] **T01 — Crear la app `orders`**
  RF: — (infraestructura)
  Hecho cuando: existe `apps/orders/` con la estructura de `plan.md`
  (sección 1), está en `INSTALLED_APPS`, y `python manage.py check` no
  reporta errores.

- [x] **T02 — Registrar `urls.py` del módulo**
  RF: — (infraestructura)
  Hecho cuando: `config/urls.py` incluye `apps.orders.urls` bajo `/api/`,
  y una request a una ruta aún no implementada devuelve 404 (no 500 ni
  error de importación).

---

## Fase 1 — Modelo de datos

- [x] **T03 — Modelo `Table`**
  RF: RF-1
  Hecho cuando: existe el modelo con `number` (`PositiveIntegerField`,
  `unique=True`) y `status` (choices `FREE`/`OCCUPIED`/`PAID`, default
  `FREE`), y la migración aplica sin errores.

- [x] **T04 — Modelo `Order`**
  RF: RF-2, RF-5, RF-8, RF-9, RF-11
  Hecho cuando: existe el modelo con `table_number`
  (`PositiveIntegerField`, sin FK a `Table`), `waiter`
  (`ForeignKey(User, on_delete=PROTECT)`), `status` (choices
  `DRAFT`/`IN_PROGRESS`/`CHARGED`/`VOIDED`, default `DRAFT`),
  `delivered` (`BooleanField`, default `False`) y `created_at`, y la
  migración aplica sin errores.

- [x] **T05 — Modelo `OrderItem`**
  RF: RF-3, RF-4, RF-5, RF-6
  Hecho cuando: existe el modelo con `order` (FK `CASCADE`),
  `catalog_product` (`ForeignKey('menu.Product', null=True,
  on_delete=SET_NULL)`), `name`, `unit_price` (`DecimalField(10,2)`),
  `quantity` (`PositiveIntegerField`, default `1`), `note` (máx. 200,
  blank), `line_type` (choices `ORIGINAL`/`ADDITION`), `is_voided`
  (default `False`) y `void_reason` (nullable), y la migración aplica
  sin errores.

- [x] **T06 — Modelo `OrderAction`**
  RF: RF-12
  Hecho cuando: existe el modelo con `order` (FK `PROTECT`),
  `action_type` (choices `ITEM_VOIDED`/`ORDER_VOIDED`/
  `ORDER_VOIDED_AUTO`/`TABLE_CORRECTED`/`CHARGED`), `performed_by` (FK
  `PROTECT`), `reason` (nullable), `item` (FK `OrderItem`, nullable,
  `PROTECT`), `from_table_number`/`to_table_number` (nullable) y
  `timestamp`, y la migración aplica sin errores.

---

## Fase 2 — Servicios de negocio (`services.py`)

- [x] **T07 — `resize_tables()`: subir el número de mesas**
  RF: RF-1
  Hecho cuando: subir el número de N a M crea las mesas N+1..M, todas en
  estado libre.

- [x] **T08 — `resize_tables()`: bajar el número de mesas**
  RF: RF-1
  Hecho cuando: bajar el número elimina las mesas de numeración más alta
  hasta el nuevo total; rechaza el cambio completo si alguna de las que
  se eliminarían no está libre; rechaza bajar por debajo de 1.

- [x] **T09 — `create_order()`**
  RF: RF-2
  Hecho cuando: crear un pedido en una mesa libre lo deja en "borrador",
  asociado al mesero, y cambia la mesa a "ocupada"; sobre una mesa no
  libre se rechaza; una mesa ocupada nunca tiene más de un pedido activo
  a la vez.

- [x] **T10 — `remove_item()` (quitar ítem en borrador)**
  RF: RF-2
  Hecho cuando: quitar un ítem de un pedido en "borrador" borra la línea
  por completo, sin exigir motivo ni dejar rastro en `OrderAction`.

- [x] **T11 — `add_item()`: validaciones y copia de datos**
  RF: RF-3, RF-4
  Hecho cuando: un ítem de catálogo copia nombre y precio vigentes (sin
  volver a leerlos después); un ítem fuera de carta exige nombre no
  vacío (≤100 caracteres) y precio manual >0; la nota es opcional y
  rechaza más de 200 caracteres; nombres repetidos entre ítems fuera de
  carta se permiten sin restricción.

- [x] **T12 — `add_item()`: revalidación de disponibilidad**
  RF: RF-3
  Hecho cuando: agregar un producto del catálogo que ya no está
  disponible se rechaza, incluso si el menú del cliente todavía lo
  mostraba como disponible.

- [x] **T13 — `add_item()`: tipo de línea y bloqueo por estado**
  RF: RF-5
  Hecho cuando: un ítem agregado con el pedido en "borrador" queda
  `ORIGINAL`; agregado con el pedido "en preparación" queda `ADDITION`;
  se rechaza si el pedido está "cobrado" o "anulado".

- [x] **T14 — `update_item_note()`**
  RF: RF-4
  Hecho cuando: se puede editar el texto de una nota ya guardada
  mientras su ítem no esté anulado y el pedido no esté cobrado ni
  anulado; se rechaza en cualquiera de esos dos casos.

- [x] **T15 — `send_order()`**
  RF: RF-5
  Hecho cuando: enviar un pedido en "borrador" lo cambia a "en
  preparación"; se rechaza si no tiene ningún ítem; reenviar un pedido
  que ya no está en "borrador" no tiene efecto y no es un error.

- [x] **T16 — `void_item()`**
  RF: RF-6
  Hecho cuando: anular un ítem de un pedido propio "en preparación"
  exige motivo, lo marca anulado sin borrar la línea, y lo excluye del
  total; se rechaza sobre un pedido ajeno o que no esté "en
  preparación"; deja una fila en `OrderAction` con los datos correctos.

- [x] **T17 — Anulación automática del pedido completo**
  RF: RF-6, RF-11
  Hecho cuando: al anular el último ítem activo de un pedido "en
  preparación", el pedido pasa a "anulado" y su mesa vuelve a "libre" de
  inmediato, reutilizando el mismo mesero y motivo de esa anulación de
  ítem (fila `ORDER_VOIDED_AUTO`, sin pedir un motivo nuevo).

- [x] **T18 — `fix_table()`**
  RF: RF-7
  Hecho cuando: corregir la mesa de un pedido propio exige que la mesa
  destino esté libre (incluida la misma mesa actual, que nunca está
  libre de sí misma), libera la mesa original, y dueño del pedido nunca
  cambia; se rechaza sobre un pedido ajeno o "cobrado"/"anulado".

- [x] **T19 — `set_delivered()`**
  RF: RF-8
  Hecho cuando: marcar/desmarcar "entregado" funciona en cualquier
  estado excepto "anulado" (donde se rechaza), sin exigir motivo.

- [x] **T20 — `charge_order()`**
  RF: RF-9
  Hecho cuando: cobrar el pedido de una mesa ocupada lo pasa a "cobrado"
  y la mesa a "pagada"; se rechaza si lo intenta un mesero o si la mesa
  no está ocupada; deja una fila `CHARGED` en `OrderAction` sin motivo.

- [x] **T21 — `release_table()`**
  RF: RF-10
  Hecho cuando: cualquier mesero puede liberar una mesa "pagada"
  (vuelve a "libre"), sin importar quién tomó el pedido; se rechaza si
  la mesa no está pagada.

- [x] **T22 — `void_order()`**
  RF: RF-11
  Hecho cuando: un admin puede anular un pedido completo en "borrador" o
  "en preparación" con motivo (libera la mesa de inmediato); se rechaza
  si lo intenta un mesero o si el pedido ya está "cobrado".

- [x] **T23 — `notify_orders_changed()` (stub) e integración**
  RF: RF-6 (plan, sección 4)
  Hecho cuando: la función existe (sin publicar todavía en Channels —
  eso es la Fase 4) y se llama exactamente al enviar un pedido (T15),
  agregar una adición (T13), anular un ítem (T16) y anular un pedido
  completo manual o automático (T17, T22); no se llama al crear el
  borrador, cobrar, marcar entregado ni liberar mesa.

---

## Fase 3 — Endpoints de la API

- [x] **T24 — Permisos: reutilizar `IsAdmin`/`IsMesero` + `IsOrderOwner`**
  RF: RF-13
  Hecho cuando: `apps/orders/permissions.py` importa `IsAdmin`/`IsMesero`
  de `apps.accounts` y define `IsOrderOwner` (permiso de objeto:
  `request.user == order.waiter`).

- [x] **T25 — `GET /api/mesas`**
  RF: RF-1, RF-13
  Hecho cuando: un admin o mesero autenticado recibe la lista de mesas
  con su número y estado; sin sesión devuelve 401.

- [x] **T26 — `PATCH /api/mesas/numero`**
  RF: RF-1
  Hecho cuando: un admin puede subir/bajar el número de mesas (200); un
  mesero recibe 403; un número <1 o no entero devuelve 400; bajar
  eliminando una mesa no libre devuelve 409.

- [x] **T27 — `POST /api/pedidos`**
  RF: RF-2
  Hecho cuando: un mesero crea un pedido en una mesa libre (201); sobre
  una mesa no libre devuelve 409; un admin recibe 403.

- [x] **T28 — `GET /api/pedidos/mios`**
  RF: RF-8, RF-10, RF-13
  Hecho cuando: un mesero autenticado recibe solo sus propios pedidos
  (con `estado`, `entregado`, `total`); sin sesión devuelve 401.

- [x] **T29 — `GET /api/pedidos/entrantes`**
  RF: soporta RF-9, RF-11
  Hecho cuando: un admin recibe los pedidos "en preparación" (excluye
  cobrados/anulados); un mesero recibe 403.

- [x] **T30 — `GET /api/pedidos/{id}`**
  RF: RF-13
  Hecho cuando: el dueño del pedido o un admin recibe el detalle
  completo; un mesero ajeno recibe 403; un id inexistente, 404.

- [x] **T31 — `POST /api/pedidos/{id}/items`**
  RF: RF-3, RF-4, RF-5
  Hecho cuando: el dueño del pedido agrega un ítem de catálogo
  (`producto_id`) o fuera de carta (`nombre`+`precio`), con `cantidad`
  y `nota` opcionales (201); valida y responde 400/404/409 según T11-T13;
  un mesero ajeno recibe 403.

- [x] **T32 — `DELETE /api/pedidos/{id}/items/{item_id}`**
  RF: RF-2
  Hecho cuando: el dueño quita un ítem de un pedido en "borrador" (204);
  si el pedido ya no está en "borrador" devuelve 409; ajeno, 403.

- [x] **T33 — `POST /api/pedidos/{id}/items/{item_id}/anular`**
  RF: RF-6
  Hecho cuando: el dueño anula un ítem de un pedido "en preparación" con
  motivo (200); sin motivo, 400; pedido no en preparación o ítem ya
  anulado, 409; ajeno, 403.

- [x] **T34 — `PATCH /api/pedidos/{id}/items/{item_id}/nota`**
  RF: RF-4
  Hecho cuando: el dueño edita la nota de un ítem activo (200); nota
  >200 caracteres, 400; ítem anulado o pedido cobrado/anulado, 409;
  ajeno, 403.

- [x] **T35 — `POST /api/pedidos/{id}/enviar`**
  RF: RF-5
  Hecho cuando: el dueño envía un pedido con al menos un ítem (200);
  sin ítems, 409; reenviar uno ya enviado responde 200 sin cambios;
  ajeno, 403.

- [x] **T36 — `POST /api/pedidos/{id}/mesa`**
  RF: RF-7
  Hecho cuando: el dueño corrige la mesa hacia una mesa libre (200);
  mesa destino no libre (incluida la misma mesa actual) o pedido
  cobrado/anulado, 409; mesa destino inexistente, 400; ajeno, 403.

- [x] **T37 — `POST /api/pedidos/{id}/entregado`**
  RF: RF-8
  Hecho cuando: el dueño marca/desmarca entregado en cualquier estado
  no anulado (200); en un pedido anulado, 409; ajeno, 403.

- [x] **T38 — `POST /api/pedidos/{id}/cobrar`**
  RF: RF-9
  Hecho cuando: un admin cobra el pedido de una mesa ocupada (200); un
  mesero recibe 403; mesa no ocupada, 409.

- [x] **T39 — `POST /api/pedidos/{id}/anular`**
  RF: RF-11
  Hecho cuando: un admin anula un pedido completo con motivo (200); sin
  motivo, 400; ya cobrado, 409; un mesero recibe 403.

- [x] **T40 — `POST /api/mesas/{numero}/liberar`**
  RF: RF-10
  Hecho cuando: cualquier mesero libera una mesa pagada (200), sin
  importar quién tomó el pedido; mesa no pagada, 409; un admin recibe
  403.

---

## Fase 4 — Propagación en tiempo real (Channels)

- [x] **T41 — `OrderConsumer`**
  RF: soporte de RF-9, RF-11 (plan, sección 4)
  Hecho cuando: un `WebsocketCommunicator` con sesión de admin válida
  conecta y queda unido al grupo `"orders_admin"`; una sesión de mesero
  o sin sesión válida es rechazada al conectar.

- [x] **T42 — `routing.py` + wiring en `config/asgi.py`**
  RF: — (infraestructura, reutiliza Channels de 002-gestion-menu)
  Hecho cuando: `/ws/pedidos/` se agrega al `websocket_urlpatterns` que
  ya expone `config/asgi.py`, sin romper `/ws/menu/` ni las rutas HTTP
  existentes.

- [x] **T43 — Conectar `notify_orders_changed()` con `group_send` real**
  RF: soporte de RF-9, RF-11
  Hecho cuando: un admin conectado a `/ws/pedidos/` recibe el evento
  `{"type": "pedidos.actualizado"}` al enviar un pedido, agregar una
  adición, anular un ítem, o anular un pedido completo (manual o
  automático); no recibe nada al crear un borrador, cobrar, marcar
  entregado ni liberar una mesa.

---

## Fase 5 — Tests

- [x] **T44 — Unit tests de mesas (T07, T08)**
  RF: RF-1
  Hecho cuando: cubren subir/bajar el número de mesas, el rechazo por
  mesa no libre, y el mínimo de 1; todos pasan.

- [x] **T45 — Unit tests de creación de pedido y quitar ítem (T09, T10)**
  RF: RF-2
  Hecho cuando: cubren crear pedido en mesa libre, el rechazo si no está
  libre, el único pedido activo por mesa, y quitar un ítem en borrador
  sin rastro; todos pasan.

- [x] **T46 — Unit tests de agregar ítem (T11-T13)**
  RF: RF-3, RF-4, RF-5
  Hecho cuando: cubren copia de nombre/precio de catálogo, validación de
  ítem fuera de carta, límite de nota, revalidación de disponibilidad, y
  el tipo de línea (`ORIGINAL`/`ADDITION`) según el estado del pedido;
  todos pasan.

- [x] **T47 — Unit tests de edición de nota (T14)**
  RF: RF-4
  Hecho cuando: cubren editar una nota mientras el ítem y el pedido
  siguen activos, y el rechazo si el ítem está anulado o el pedido
  cobrado/anulado; todos pasan.

- [x] **T48 — Unit tests de envío (T15)**
  RF: RF-5
  Hecho cuando: cubren el cambio de estado, el rechazo si no tiene
  ítems, y el reenvío ignorado sin error; todos pasan.

- [x] **T49 — Unit tests de anulación de ítem y auto-anulación (T16, T17)**
  RF: RF-6, RF-11
  Hecho cuando: cubren anular con motivo, la exclusión del total, el
  rechazo por pedido ajeno o fuera de "en preparación", y la anulación
  automática del pedido completo (con liberación de mesa) al quedar sin
  ítems activos; todos pasan.

- [x] **T50 — Unit tests de corrección de mesa (T18)**
  RF: RF-7
  Hecho cuando: cubren la corrección hacia mesa libre, el rechazo hacia
  la misma mesa o una no libre, el rechazo por pedido ajeno o
  cobrado/anulado, y que el dueño nunca cambia; todos pasan.

- [x] **T51 — Unit tests de "Entregado" (T19)**
  RF: RF-8
  Hecho cuando: cubren marcar/desmarcar en borrador, en preparación y
  cobrado, y el rechazo en anulado; todos pasan.

- [x] **T52 — Unit tests de cobro y liberación (T20, T21)**
  RF: RF-9, RF-10
  Hecho cuando: cubren el cobro exitoso, el rechazo por rol o por mesa
  no ocupada, la liberación exitosa por cualquier mesero, y el rechazo
  si la mesa no está pagada; todos pasan.

- [x] **T53 — Unit tests de anulación de pedido completo (T22)**
  RF: RF-11
  Hecho cuando: cubren la anulación en borrador y en preparación, el
  rechazo por rol o por estar ya cobrado, y la liberación de la mesa;
  todos pasan.

- [x] **T54 — Unit tests de disparo de notificación (T23)**
  RF: RF-6 (plan, sección 4)
  Hecho cuando: confirman que `notify_orders_changed()` se llama
  exactamente en enviar/adición/anular ítem/anular pedido, y no se llama
  al crear borrador, cobrar, marcar entregado ni liberar mesa; todos
  pasan.

- [x] **T55 — Integration tests de endpoints de mesas (T25, T26, T40)**
  RF: RF-1, RF-10
  Hecho cuando: cada código de respuesta (200/400/401/403/409) de esos
  tres endpoints tiene al menos un test, y todos pasan.

- [x] **T56 — Integration tests de creación/lectura de pedidos (T27-T30)**
  RF: RF-2, RF-8, RF-9, RF-10, RF-13
  Hecho cuando: cada código de respuesta de esos cuatro endpoints tiene
  al menos un test, y todos pasan.

- [x] **T57 — Integration tests de endpoints de ítems (T31-T34)**
  RF: RF-2, RF-3, RF-4, RF-5, RF-6
  Hecho cuando: cada código de respuesta de esos cuatro endpoints tiene
  al menos un test, y todos pasan.

- [x] **T58 — Integration tests de endpoints de estado del pedido (T35-T39)**
  RF: RF-5, RF-7, RF-8, RF-9, RF-11
  Hecho cuando: cada código de respuesta de esos cinco endpoints tiene
  al menos un test, y todos pasan.

- [x] **T59 — Integration test: flujo completo**
  RF: RF-1, RF-2, RF-3, RF-5, RF-6, RF-7, RF-8, RF-9, RF-10
  Hecho cuando: un test end-to-end reproduce ajustar mesas → crear
  pedido → enviar → agregar adición → anular un ítem (verifica
  `OrderAction`) → corregir mesa → marcar entregado → cobrar → liberar
  mesa.

- [x] **T60 — Integration tests de permisos y autenticación (RF-13)**
  RF: RF-13
  Hecho cuando: cada endpoint de la Fase 3 tiene un test que confirma
  401 sin sesión y 403 para el rol/dueño incorrecto; un mesero ajeno no
  puede leer el contenido de un pedido que no es suyo pero sí el estado
  de esa mesa.

- [x] **T61 — Tests del canal en tiempo real (T41, T43)**
  RF: soporte de RF-9, RF-11
  Hecho cuando: cubren conexión admin/mesero/sin sesión, la recepción
  del evento en cada operación de T43, y la ausencia de evento al crear
  un borrador, cobrar, marcar entregado o liberar mesa; todos pasan.

---

## Fase 6 — Frontend

- [x] **T62 — `lib/api/orders.ts`**
  RF: RF-1 a RF-11
  Hecho cuando: expone una función por cada endpoint de la Fase 3,
  propagando los errores tal cual los devuelve la API.

- [x] **T63 — `lib/api/ordersSocket.ts`**
  RF: soporte de RF-9, RF-11
  Hecho cuando: abre `/ws/pedidos/`, reconecta con backoff ante
  desconexión, y expone un callback que se dispara al recibir
  `pedidos.actualizado`.

- [x] **T64 — Pantalla `admin/mesas`**
  RF: RF-1
  Hecho cuando: permite al admin ver y ajustar el número total de
  mesas, reflejando los errores 400/409 de T26 en la UI.

- [x] **T65 — Pantalla `mesero/mesas`**
  RF: RF-1, RF-2, RF-13
  Hecho cuando: muestra el estado (libre/ocupada/pagada) de todas las
  mesas, y permite crear un pedido nuevo sobre una mesa libre.

- [x] **T66 — Pantalla `mesero/pedidos/[id]`**
  RF: RF-3, RF-4, RF-5, RF-6, RF-7
  Hecho cuando: permite agregar productos del catálogo (de una lista) o
  ítems fuera de carta con nota, enviar el pedido, agregarle adiciones,
  anular un ítem con motivo, y corregir su mesa — todo reflejando los
  errores de T31-T36 en la UI.

- [x] **T67 — Pantalla `mesero/pedidos`**
  RF: RF-8, RF-10
  Hecho cuando: lista los pedidos propios del mesero con un botón
  rápido de marcar/desmarcar "Entregado", y un botón de "Liberar mesa"
  cuando corresponde (mesa pagada).

- [x] **T68 — Pantalla `admin/pedidos`**
  RF: soporte de RF-9, RF-11
  Hecho cuando: muestra los pedidos entrantes, se refresca sola al
  recibir un evento de `ordersSocket.ts` o al presionar un botón
  manual, y permite cobrar un pedido o anular un pedido completo con
  motivo, reflejando los errores de T38-T39 en la UI.

---

## Fase 7 — Número del día (RF-14)

- [x] **T69 — `TIME_ZONE` a `America/Bogota`**
  RF: RF-14 (soporte)
  Hecho cuando: `config/settings.py` tiene `TIME_ZONE = "America/Bogota"`
  (antes `"UTC"`); `python manage.py check` no reporta errores; un test
  confirma que `django.utils.timezone.localdate()` refleja la fecha de
  Bogotá, no la de UTC, para un instante cercano a medianoche donde
  ambas difieren.

- [x] **T70 — Modelo `DailyOrderCounter`**
  RF: RF-14
  Hecho cuando: existe el modelo con `local_date` (`DateField`,
  `primary_key=True`) y `last_number` (`PositiveIntegerField`, default
  `0`), y la migración aplica sin errores.

- [x] **T71 — Campos `daily_number`/`sent_at` en `Order`**
  RF: RF-14
  Hecho cuando: `Order` gana `daily_number`
  (`PositiveIntegerField(null=True, blank=True)`) y `sent_at`
  (`DateTimeField(null=True, blank=True)`); la migración aplica sin
  errores; los pedidos ya existentes quedan con ambos campos en `None`
  (sin backfill retroactivo).

- [x] **T72 — `asignar_numero_del_dia()` con lock dedicado**
  RF: RF-14
  Hecho cuando: la función usa un `threading.Lock()` propio (distinto
  del de `kitchen_printing`) para incrementar `DailyOrderCounter` de la
  fecha local actual (`get_or_create` + `last_number += 1`) y asignar
  `daily_number`/`sent_at = timezone.now()` al pedido; un test con dos
  hilos llamándola "simultáneamente" confirma que nunca produce el
  mismo número para el mismo día (mismo patrón que
  `PrintLockSerializationTests` de 004).

- [x] **T73 — Integrar la asignación en `send_order()`**
  RF: RF-14
  Hecho cuando: la transición real de "borrador" a "en preparación"
  llama a `asignar_numero_del_dia()` dentro de la misma transacción,
  antes de guardar; un reenvío sin efecto (pedido que ya no está en
  "borrador") no la llama ni modifica los campos existentes; un pedido
  que nunca se envía nunca los recibe.

- [x] **T74 — Inmutabilidad ante adiciones/anulaciones/corrección de mesa**
  RF: RF-14
  Hecho cuando: agregar una adición, anular un ítem, anular el pedido
  completo (manual o automático), o corregir la mesa de un pedido ya
  enviado, dejan `daily_number` y `sent_at` exactamente iguales a como
  quedaron en el envío original.

- [x] **T75 — Serializar `numero_dia`/`enviado_en` en los payloads de pedido**
  RF: RF-14
  Hecho cuando: las respuestas de `POST /api/pedidos`, `POST
  /api/pedidos/{id}/enviar`, `POST /api/pedidos/{id}/mesa`, `POST
  /api/pedidos/{id}/entregado`, y `GET /api/pedidos/mios`, `/entrantes`,
  `/{id}` incluyen `numero_dia` (entero o `null`) y `enviado_en` (ISO
  datetime o `null`); el campo `id` interno sigue presente sin cambios
  en todas ellas.

- [x] **T76 — `numero_dia_pedido_activo` en `GET /api/mesas`**
  RF: RF-14 (interacción con RF-13)
  Hecho cuando: cada mesa "ocupada" o "pagada" en la respuesta incluye
  el `daily_number` de su pedido activo, visible igual para el mesero
  dueño y para cualquier otro mesero autenticado; una mesa "libre", o un
  pedido activo todavía sin número (caso transitorio), devuelven `null`.

- [x] **T77 — Unit tests de asignación e inmutabilidad (T72-T74)**
  RF: RF-14
  Hecho cuando: cubren primer pedido del día (`1`), segundo pedido
  (`2`), reinicio en una fecha local distinta (mockeada), reenvío sin
  efecto, inmutabilidad ante adiciones/anulaciones/corrección de mesa, y
  la serialización concurrente de dos asignaciones casi simultáneas;
  todos pasan.

- [x] **T78 — Integration tests de `numero_dia`/`enviado_en`/
  `numero_dia_pedido_activo` (T75-T76)**
  RF: RF-14
  Hecho cuando: cada endpoint tocado por T75 y T76 tiene al menos un
  test confirmando `null` antes de enviar y los valores reales después;
  un mesero ajeno recibe el `numero_dia_pedido_activo` de una mesa
  ocupada por otro mesero, pero sigue recibiendo 403 al pedir el
  contenido completo de ese pedido en `GET /api/pedidos/{id}`; todos
  pasan.

- [x] **T79 — Frontend: `TableGrid.tsx` muestra el número del día**
  RF: RF-14
  Hecho cuando: la cuadrícula de mesas del mesero muestra "N° {numero}"
  junto al estado de cada mesa ocupada o pagada, usando
  `numero_dia_pedido_activo`; no muestra nada en una mesa libre ni
  cuando ese valor es `null`.

- [x] **T80 — Frontend: título de pedido en `MyOrdersList.tsx` e
  `IncomingOrdersPanel.tsx`**
  RF: RF-14
  Hecho cuando: el título de cada pedido en ambas listas pasa de
  "Pedido {id}" a "N° {numero_dia}", con la fecha/hora de envío (texto
  más pequeño, menor jerarquía visual) junto al número; ninguna de las
  dos pantallas sigue mostrando el identificador interno como texto.

---

## Fase 8 — Etiqueta visible de "Entregado" (RF-8)

- [x] **T81 — Badge de estado muestra "Entregado" cuando corresponda**
  RF: RF-8
  Hecho cuando: en `MyOrdersList.tsx` y en `OrderBuilder.tsx`, el badge
  de estado que ve el mesero sigue esta regla sin tocar
  `Order.status`/`Order.delivered` en el backend: "anulado" → "Anulado";
  "cobrado" → "Cobrado" (sin importar `delivered`); "en preparación" con
  `delivered=true` → "Entregado" (badge nuevo, color
  `var(--status-free)`); "en preparación" con `delivered=false` → "En
  preparación" (igual que hoy); "borrador" → "Borrador". Ningún
  endpoint, servicio ni test de `apps.orders`/`apps.payments`/
  `apps.kitchen_printing` cambia — la suite de backend sigue en
  651/651.

---

## Fase 9 — Mesas retenidas por pedidos olvidados (RF-15)

- [x] **T82 — Backend: limpieza de borradores vacíos y recordatorio**
  RF: RF-15
  Hecho cuando: `discard_stale_empty_drafts()` elimina los borradores sin
  ítems con más de 10 minutos y libera su mesa (llamado desde
  `create_order`, `GET /api/mesas`, `GET /api/pedidos/mios` y
  `GET /api/mesas/ocupadas`); nunca toca un borrador con ítems ni un
  pedido enviado; `OrderSerializer` expone `created_at` y
  `draft_reminder`. Tests en `apps/orders/tests/test_stale_orders.py`.

- [x] **T83 — Backend: `GET /api/mesas/ocupadas`**
  RF: RF-15
  Hecho cuando: el endpoint (solo admin) devuelve cada mesa ocupada con
  su pedido activo e `is_stale` (más de 3 horas); 401 sin sesión, 403
  mesero; el admin puede anular un borrador con el endpoint de RF-11.

- [x] **T84 — Frontend: borrar el borrador vacío al salir y aviso al mesero**
  RF: RF-15
  Hecho cuando: `OrderBuilder` elimina al desmontarse un borrador sin
  ítems (nunca uno con ítems ni uno enviado); `MyOrdersList` muestra
  "Borrador sin enviar" cuando `draft_reminder` es verdadero.

- [x] **T85 — Frontend: mesas ocupadas en el panel del admin**
  RF: RF-15
  Hecho cuando: `/admin/mesas` muestra `OccupiedTablesPanel` (mesa,
  estado, mesero, desde cuándo, ítems, total, "Anular pedido" con
  motivo, borde rojo y aviso para las de más de 3 horas);
  `IncomingOrdersPanel` muestra "Hay N mesas ocupadas desde hace más de
  3 horas" con enlace a Mesas.

---

## Fase 10 — Eliminar borrador (admin), mesero en Entrantes y "Mis pedidos" por día (RF-9, RF-15, RF-16)

- [x] **T86 — "Eliminar borrador" del admin y borradores de días anteriores**
  RF: RF-11, RF-12, RF-15
  Hecho cuando: `POST /api/pedidos/{id}/eliminar-borrador` (solo admin,
  `services.discard_draft_by_admin`) anula el borrador con el motivo
  fijo "Borrador eliminado por el admin", registra quién y cuándo, y
  libera la mesa (409 si ya se envió); `OccupiedTablesPanel` muestra
  "Eliminar borrador" con confirmación en los borradores y "Anular
  pedido" con motivo en los enviados; `discard_stale_drafts()` también
  elimina todo borrador de un día anterior, tenga o no ítems. Tests en
  `test_stale_orders.py`, `OccupiedTablesPanel.test.tsx` y
  `lib/api/orders.test.ts`.

- [x] **T87 — Mesero en el panel de pedidos entrantes**
  RF: RF-9
  Hecho cuando: cada tarjeta de `IncomingOrdersPanel` muestra
  "Mesero: {usuario}".

- [x] **T88 — "Mis pedidos" por día**
  RF: RF-16
  Hecho cuando: `GET /api/pedidos/mios?fecha=` devuelve los del día
  (por defecto hoy, más los pendientes de días anteriores) y 400 con
  fecha inválida; `MyOrdersList` tiene selector de fecha (hoy por
  defecto, sin fechas futuras) y mensaje vacío. Tests en
  `test_views_my_orders.py`, `MyOrdersList.test.tsx` y
  `lib/api/orders.test.ts`.

- [x] **T89 — Frontend: "Eliminar" ítem en borrador**
  RF: RF-2
  Hecho cuando: en `OrderBuilder.tsx`, cada ítem de un pedido en
  "borrador" muestra "Eliminar", que quita la línea sin pedir motivo
  (`DELETE /api/pedidos/{id}/items/{item_id}`, ya existente) y refresca
  el pedido; una vez enviado, el ítem solo ofrece "Anular" con motivo
  (RF-6). Tests en `OrderBuilder.test.tsx`.

---

## Fase 11 — Total por línea y nota del admin (RF-3, RF-17)

- [x] **T90 — Total por línea y total del pedido**
  RF: RF-3
  Hecho cuando: `OrderItemSerializer` expone `line_total`;
  `OrderBuilder` muestra "c/u" y el total de cada línea, y una fila
  "Total" al final; `ChargeOrderModal` y `ChargedOrdersPanel` usan
  `line_total` en vez de multiplicar en el frontend.

- [x] **T91 — Nota del pedido solo para el admin**
  RF: RF-17
  Hecho cuando: `Order.admin_note` (migración `0006`),
  `PATCH /api/pedidos/{id}/nota-admin` (solo admin; 400 si pasa de 300
  caracteres, 403 mesero, 404); `AdminOrderSerializer` la incluye solo
  en las vistas de admin; `AdminNoteEditor` en Entrantes y Cobrados.
  Tests en `test_admin_note_line_total.py` y `AdminNoteEditor.test.tsx`.
