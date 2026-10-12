# 003 · Mesas y pedidos — Plan técnico

Este plan traduce a diseño técnico (el "cómo") la especificación aprobada
en `spec.md` (el "qué/por qué"). No contiene código, solo estructura,
contratos, pseudocódigo y decisiones justificadas.

> **Nota de alcance**: el prompt original de este plan describía la tabla
> `Mesa` con un campo `activa` y la tabla `Pedido` con un campo separado
> de "historial de cambios de mesa". La spec ya resuelta (RF-1) no usa un
> booleano `activa` — una mesa se crea o se elimina por completo según el
> rango 1..N (nunca queda "inactiva"), y el historial de cambios de mesa
> vive en la tabla de auditoría `OrderAction` (sección 2), no como un
> campo propio de `Order`. También se añade `quantity` (cantidad) a
> `OrderItem`, que la spec nunca prohíbe ni exige explícitamente — es una
> decisión de este plan (sección 5, decisión 6).

## Cumplimiento de `docs/constitution.md`

- **Regla 1 (stack mínimo)**: solo Django + DRF + Django Channels +
  Next.js + SQLite; reutiliza el `ProtocolTypeRouter` y el
  `CHANNEL_LAYERS` en memoria que ya instaló y configuró
  [`002-gestion-menu`](../002-gestion-menu/plan.md) — no se agrega
  infraestructura nueva. La asignación del número del día (RF-14,
  sección 4.1) reutiliza el mismo patrón de `threading.Lock()` en
  memoria del proceso que ya usa `kitchen_printing` (004) para
  serializar el acceso a la impresora — nada de Redis ni de un servicio
  externo de secuencias.
- **Regla 2 (offline-first en LAN)**: todos los endpoints de mesas y
  pedidos son REST/WebSocket sobre la LAN local; ninguno depende de un
  servicio externo. El cálculo de "medianoche hora local" (RF-14) usa
  `TIME_ZONE = "America/Bogota"` en `config/settings.py` (hoy `"UTC"`,
  cambia como parte de esta implementación) y el reloj del propio
  equipo — no consulta ningún servicio de hora externo.
- **Regla 3 (contrato de API)**: Next.js nunca toca SQLite directamente;
  todo pasa por los endpoints de la sección 3 y el canal de la sección 4.
- **Regla 4 (trazabilidad)**: el modelo `OrderAction` (sección 2) registra
  quién/cuándo/por qué en anulación de ítem, anulación de pedido completo
  y corrección de mesa, y quién/cuándo (sin motivo) en el cobro.
- **Regla 5 (permisos por rol)**: permisos de DRF (sección 1,
  `permissions.py`) separan estrictamente qué puede hacer un mesero sobre
  sus propios pedidos, qué puede hacer cualquier mesero (liberar mesa), y
  qué es exclusivo de admin (cobrar, anular pedido completo, ajustar el
  número de mesas).
- **Regla 6 (tests obligatorios)**: sección 6 cubre el 100% de los
  endpoints y acciones sensibles.
- **Regla 7 (idioma)**: nombres de clases/campos/variables en inglés en
  el código real (`Table`, `Order`, `OrderItem`, `is_voided`, etc.); este
  documento permanece en español.

---

## 1. Estructura de módulos/archivos

### Backend (`/backend`)

```
backend/
  apps/
    orders/                     # app dedicada a este módulo (RF-1..RF-13)
      models.py                 # Table, Order, OrderItem, OrderAction,
                                 # DailyOrderCounter (RF-14, sección 4.1)
      serializers.py            # 1 serializer por forma de respuesta de
                                 # la sección 3
      permissions.py            # reutiliza IsAdmin/IsMesero de
                                 # apps.accounts; agrega IsOrderOwner
                                 # (permiso de objeto: request.user ==
                                 # order.waiter)
      services.py                # lógica de negocio pura: resize de
                                 # mesas, crear pedido, agregar ítem,
                                 # quitar/anular ítem, enviar (asigna el
                                 # número del día, RF-14), corregir
                                 # mesa, entregado, cobrar, liberar,
                                 # anular pedido — sin dependencias de
                                 # HTTP, testeable como unit test
                                 # (sección 6)
      views.py                  # 1 APIView por endpoint de la sección 3
      urls.py                   # incluido en config/urls.py bajo /api/
      consumers.py                # OrderConsumer — feed del admin (RF-6
                                   # del prompt de este plan: tiempo real)
      routing.py                   # websocket_urlpatterns: /ws/pedidos/
      tests/
        test_models.py
        test_services_tables.py
        test_services_orders.py
        test_services_items.py
        test_services_daily_number.py  # RF-14, sección 4.1
        test_views_tables.py
        test_views_orders.py
        test_views_items.py
        test_views_delivered_release.py
        test_permissions.py
        test_consumers.py
        test_realtime_propagation.py
        test_flujo_pedido_completo.py
```

`config/asgi.py` solo agrega una línea al `websocket_urlpatterns` que ya
existe desde 002 (ver sección 4) — no se reinstala `channels` ni
`daphne`, ya están en `requirements.txt` desde 002-gestion-menu.

### Frontend (`/frontend`, Next.js App Router)

```
frontend/
  app/
    admin/(panel)/
      mesas/page.tsx              # RF-1 — ajustar el número de mesas
      pedidos/page.tsx             # ver pedidos entrantes en tiempo
                                    # real (sección 4), cobrar (RF-9),
                                    # anular pedido completo (RF-11)
    mesero/(turno)/
      mesas/page.tsx                # RF-1 (lectura), RF-2, RF-13 — ve
                                     # el estado de todas las mesas y
                                     # crea un pedido en una libre
      pedidos/
        page.tsx                     # "Mis pedidos": lista con botón
                                      # rápido "Entregado" (RF-8) y
                                      # "Liberar mesa" (RF-10) cuando
                                      # corresponda
        [id]/page.tsx                 # armar/editar un pedido: ítems de
                                       # catálogo o fuera de carta (RF-3),
                                       # notas (RF-4), enviar y
                                       # adiciones (RF-5), anular ítem
                                       # (RF-6), corregir mesa (RF-7)
  lib/api/
    orders.ts                       # llamadas REST de la sección 3
    ordersSocket.ts                  # conexión a /ws/pedidos/, solo se
                                      # monta en admin/pedidos (RF-6 de
                                      # este plan)
  components/
    TableCountSettings.tsx            # RF-1 (admin)
    TableGrid.tsx                      # RF-1 (lectura), RF-2 (mesero);
                                        # + "N° {numero_dia_pedido_activo}"
                                        # junto al estado de cada mesa (RF-14)
    OrderBuilder.tsx                    # RF-3, RF-4, RF-5, RF-6, RF-7
    MyOrdersList.tsx                     # RF-8, RF-10; título de cada
                                          # pedido pasa de "Pedido {id}" a
                                          # "N° {numero_dia}" + fecha/hora
                                          # en letra pequeña (RF-14)
    IncomingOrdersPanel.tsx                # RF-9, RF-11 (admin); mismo
                                            # cambio de título que
                                            # MyOrdersList (RF-14)
```

---

## 2. Modelo de datos

### Tabla `Table` (mesa — RF-1)

| Campo    | Tipo                                                        | Restricciones                                    | RF   |
|----------|--------------------------------------------------------------|----------------------------------------------------|------|
| `id`     | `AutoField`                                                   | PK                                                  | —    |
| `number` | `PositiveIntegerField`                                        | `unique=True`; siempre el rango contiguo 1..N       | RF-1 |
| `status` | `CharField` choices `FREE` / `OCCUPIED` / `PAID`              | default `FREE`                                      | RF-1 |

`number` es un campo propio (no el `id` autoincremental de Django),
porque subir/bajar el número de mesas debe crear/eliminar filas por
numeración exacta (sección 5, decisión 1).

**Ejemplo de registro:**

```json
{ "id": 6, "number": 6, "status": "OCCUPIED" }
```

### Tabla `Order` (pedido — RF-2, RF-5, RF-8, RF-9, RF-11)

| Campo          | Tipo                                                           | Restricciones                                                  | RF        |
|-----------------|-------------------------------------------------------------------|-------------------------------------------------------------------|-----------|
| `id`            | `AutoField`                                                        | PK                                                                 | —         |
| `table_number`  | `PositiveIntegerField`                                             | copia del número de mesa al crear (RF-2) o corregir (RF-7); **no** es FK a `Table` (sección 5, decisión 1) | RF-2, RF-7 |
| `waiter`        | `ForeignKey(User, on_delete=PROTECT)`                              | el mesero que lo creó; nunca cambia (RF-7)                        | RF-2, RF-7 |
| `status`        | `CharField` choices `DRAFT` / `IN_PROGRESS` / `CHARGED` / `VOIDED` | default `DRAFT`                                                    | RF-2, RF-5, RF-9, RF-11 |
| `delivered`     | `BooleanField` default `False`                                     | independiente de `status` (RF-8)                                   | RF-8      |
| `created_at`    | `DateTimeField(auto_now_add=True)`                                 | —                                                                  | —         |
| `daily_number`  | `PositiveIntegerField(null=True, blank=True)`                      | `None` mientras el pedido esté en "borrador"; se asigna una sola vez, al enviarlo, y nunca cambia después (RF-14) | RF-14 |
| `sent_at`       | `DateTimeField(null=True, blank=True)`                             | `None` mientras esté en "borrador"; se fija junto con `daily_number`, en el mismo instante, y tampoco cambia después (RF-14) | RF-14 |

**Ejemplo de registro:**

```json
{
  "id": 41,
  "table_number": 6,
  "waiter_id": 7,
  "status": "IN_PROGRESS",
  "delivered": false,
  "created_at": "2026-03-10T20:15:00Z",
  "daily_number": 7,
  "sent_at": "2026-03-10T20:15:00Z"
}
```

No hay `UniqueConstraint` declarativa sobre `(daily_number)` solo —
`daily_number` se repite entre días distintos por diseño (RF-14); lo
único que debe ser único es el par (fecha local de `sent_at`,
`daily_number`), y esa fecha no es un campo propio de `Order` sino que
se deriva de `sent_at` en la zona horaria del servidor — por eso la
unicidad real la garantiza `DailyOrderCounter` (abajo), no una
restricción sobre esta tabla.

### Tabla `OrderItem` (línea de pedido — RF-3, RF-4, RF-5, RF-6)

| Campo             | Tipo                                                    | Restricciones                                                       | RF        |
|--------------------|------------------------------------------------------------|--------------------------------------------------------------------|-----------|
| `id`               | `AutoField`                                                 | PK                                                                  | —         |
| `order`            | `ForeignKey(Order, on_delete=CASCADE)`                      | —                                                                    | —         |
| `catalog_product`  | `ForeignKey('menu.Product', null=True, on_delete=SET_NULL)` | opcional, solo para trazabilidad/reportes; **nunca** se relee para nombre/precio | RF-3 |
| `name`             | `CharField(100)`                                             | copiado del producto o escrito a mano si es fuera de carta          | RF-3      |
| `unit_price`       | `DecimalField(max_digits=10, decimal_places=2)`              | copiado del producto, o precio manual si es fuera de carta          | RF-3      |
| `quantity`         | `PositiveIntegerField`                                       | default `1`                                                          | (sección 5, decisión 6) |
| `note`             | `CharField(200, blank=True)`                                 | opcional (RF-4)                                                      | RF-4      |
| `line_type`        | `CharField` choices `ORIGINAL` / `ADDITION`                  | `ORIGINAL` si se agregó en "borrador", `ADDITION` si en "en preparación" | RF-5  |
| `is_voided`        | `BooleanField` default `False`                               | RF-6                                                                  | RF-6      |
| `void_reason`      | `TextField(null=True, blank=True)`                            | obligatorio solo si `is_voided=True`                                 | RF-6      |
| `created_at`        | `DateTimeField(auto_now_add=True)`                            | —                                                                     | —         |

**Ejemplo de registro:**

```json
{
  "id": 108,
  "order_id": 41,
  "catalog_product_id": 12,
  "name": "Limonada natural",
  "unit_price": "4.50",
  "quantity": 2,
  "note": "sin azúcar",
  "line_type": "ORIGINAL",
  "is_voided": false,
  "void_reason": null,
  "created_at": "2026-03-10T20:15:05Z"
}
```

### Tabla `OrderAction` (trazabilidad — RF-12, regla 4 de la constitución)

| Campo          | Tipo                                                                                     | RF |
|-----------------|---------------------------------------------------------------------------------------------|----|
| `id`            | `AutoField`                                                                                  | — |
| `order`         | `ForeignKey(Order, on_delete=PROTECT)`                                                       | RF-12 |
| `action_type`   | `CharField` choices: `ITEM_VOIDED`, `ORDER_VOIDED`, `ORDER_VOIDED_AUTO`, `TABLE_CORRECTED`, `CHARGED` | RF-6, RF-7, RF-9, RF-11 |
| `performed_by`  | `ForeignKey(User, on_delete=PROTECT)`                                                        | RF-12 |
| `reason`        | `TextField(null=True)`                                                                       | RF-6, RF-11 (siempre `None` en `CHARGED`) |
| `item`          | `ForeignKey(OrderItem, null=True, on_delete=PROTECT)`                                        | solo en `ITEM_VOIDED` |
| `from_table_number` / `to_table_number` | `PositiveIntegerField(null=True)` cada uno                                  | solo en `TABLE_CORRECTED` — esta es la fila de "historial de cambios de mesa" del prompt original |
| `timestamp`     | `DateTimeField(auto_now_add=True)`                                                           | RF-12 |

**Ejemplo de registro:**

```json
{
  "id": 205,
  "order_id": 41,
  "action_type": "TABLE_CORRECTED",
  "performed_by_id": 7,
  "reason": null,
  "item_id": null,
  "from_table_number": 5,
  "to_table_number": 6,
  "timestamp": "2026-03-10T20:14:50Z"
}
```

`ORDER_VOIDED_AUTO` reutiliza `performed_by` y `reason` de la fila
`ITEM_VOIDED` que dejó al pedido sin ítems activos (RF-6), en vez de
pedir un motivo nuevo.

### Tabla `DailyOrderCounter` (contador del número del día — RF-14)

| Campo         | Tipo                                  | Restricciones                                        | RF    |
|----------------|----------------------------------------|---------------------------------------------------------|-------|
| `local_date`   | `DateField`                            | PK (`primary_key=True`); fecha local (`America/Bogota`) | RF-14 |
| `last_number`  | `PositiveIntegerField`                 | default `0`; el último número del día ya repartido      | RF-14 |

Una sola fila por día, creada perezosamente (`get_or_create`) la
primera vez que se envía un pedido ese día — nunca se precrean filas
para días futuros. Ver sección 4.1 para cómo se incrementa sin
duplicar números bajo solicitudes concurrentes.

**Ejemplo de registro:**

```json
{ "local_date": "2026-03-10", "last_number": 7 }
```

---

## 3. Contrato de la API

Todos los endpoints viven bajo `/api/`. Autenticación por cookie de
sesión (heredada del módulo 001). Todas las respuestas de error usan
`{"detail": "<mensaje>"}`.

| # | Endpoint | Método | RF | Auth | Request | Response 200/201/204 | Errores |
|---|-----------|--------|----|------|---------|------------------------|---------|
| 1 | `/api/mesas` | GET | RF-1, RF-13, RF-14 | admin o mesero | — | `[{numero, estado, numero_dia_pedido_activo}]` | 401 |
| 2 | `/api/mesas/numero` | PATCH | RF-1 | admin | `{numero}` | 200 `[{numero, estado}]` | 400 numero<1 o no entero; 409 alguna mesa a eliminar no está libre; 403 mesero |
| 3 | `/api/pedidos` | POST | RF-2 | mesero | `{mesa_numero}` | 201 `{id, mesa_numero, estado, entregado, numero_dia: null, enviado_en: null}` | 400 mesa no existe; 409 mesa no libre; 403 admin |
| 4 | `/api/pedidos/mios?fecha=AAAA-MM-DD` | GET | RF-8, RF-10, RF-13, RF-16 | mesero | — | `[{id, mesa_numero, estado, entregado, total, numero_dia, enviado_en}]` (solo del mesero autenticado; por defecto hoy más los pendientes de días anteriores, `services.my_orders_for_day`) | 400 fecha inválida; 401 |
| 5 | `/api/pedidos/entrantes` | GET | soporta RF-9, RF-11 (panel admin) | admin | — | `[{id, mesa_numero, estado, entregado, items, total, numero_dia, enviado_en, waiter_username}]` (excluye cobrados/anulados) | 403 mesero |
| 6 | `/api/pedidos/{id}` | GET | RF-13 | dueño o admin | — | `{id, mesa_numero, estado, entregado, items, total, numero_dia, enviado_en}` | 403 mesero ajeno; 404 |
| 7 | `/api/pedidos/{id}/items` | POST | RF-3, RF-4, RF-5 | dueño | `{producto_id}` **o** `{nombre, precio}`, + `cantidad?`, `nota?` | 201 (línea creada; `line_type` se infiere del estado del pedido) | 400 validación; 404 producto/pedido; 409 producto no disponible, o pedido cobrado/anulado; 403 no es el dueño |
| 8 | `/api/pedidos/{id}/items/{item_id}` | DELETE | RF-2 | dueño | — | 204 | 409 el pedido ya no está en "borrador"; 403; 404 |
| 9 | `/api/pedidos/{id}/items/{item_id}/anular` | POST | RF-6 | dueño | `{motivo}` | 200 | 400 falta motivo; 409 pedido no en preparación, o ítem ya anulado; 403; 404 |
| 10 | `/api/pedidos/{id}/items/{item_id}/nota` | PATCH | RF-4 | dueño | `{nota}` | 200 | 400 nota vacía inválida/>200; 409 ítem anulado o pedido cobrado/anulado; 403; 404 |
| 11 | `/api/pedidos/{id}/enviar` | POST | RF-5 | dueño | — | 200 | 409 sin ítems; 403; 404 (si ya no está en "borrador": 200 sin efecto) |
| 12 | `/api/pedidos/{id}/mesa` | POST | RF-7 | dueño | `{mesa_numero_destino}` | 200 | 400 mesa destino no existe; 409 mesa destino no libre (incluida la misma mesa), o pedido cobrado/anulado; 403; 404 |
| 13 | `/api/pedidos/{id}/entregado` | POST | RF-8 | dueño | `{entregado}` | 200 | 409 pedido anulado; 403; 404 |
| 14 | `/api/pedidos/{id}/cobrar` | POST | RF-9 | admin | — | 200 | 409 mesa no ocupada; 403 mesero; 404 |
| 15 | `/api/pedidos/{id}/anular` | POST | RF-11 | admin | `{motivo}` | 200 | 400 falta motivo; 409 ya cobrado; 403 mesero; 404 |
| 16 | `/api/mesas/{numero}/liberar` | POST | RF-10 | mesero (cualquiera) | — | 200 | 409 mesa no está pagada; 403 admin; 404 mesa no existe |
| 17 | `/api/mesas/ocupadas` | GET | RF-15 | admin | — | `[{number, order, is_stale}]` (`order` con el mismo formato del endpoint 6, o `null`) | 401; 403 mesero |
| 19 | `/api/pedidos/{id}/nota-admin` | PATCH | RF-17 | admin | `{note}` | 200 (pedido con `admin_note`) | 400 nota de más de 300; 403 mesero; 404 |
| 18 | `/api/pedidos/{id}/eliminar-borrador` | POST | RF-15, RF-11, RF-12 | admin | — | 200 (pedido anulado, mesa libre; `OrderAction ORDER_VOIDED` con motivo fijo `DRAFT_DISCARD_REASON`) | 409 el pedido no está en "borrador"; 403 mesero; 404 |

RF-15: `discard_stale_drafts()` (`services.py`) elimina los
borradores sin ítems con más de `EMPTY_DRAFT_TTL` (10 min) y todos los
borradores de un día anterior, y libera su mesa; se llama al inicio de los endpoints 1, 3, 4 y 17, sin tarea
programada (regla 1: no se agrega infraestructura). Todo pedido expone
`created_at` y `draft_reminder` (borrador con ítems y más de
`DRAFT_REMINDER_AFTER`, 15 min); `is_stale` del endpoint 17 compara
`created_at` con `STALE_TABLE_AFTER` (3 h). Los umbrales se calculan en
el backend, nunca en el frontend (regla 3). El borrado inmediato al salir
de la pantalla del pedido lo hace `OrderBuilder` llamando al endpoint de
eliminación de RF-2 que ya existía.

Endpoint 7 unifica "agregar ítem de catálogo", "agregar ítem fuera de
carta" y "agregar adición" en una sola ruta (sección 5, decisión 2): el
servidor decide `line_type` según si el pedido está en "borrador" u "en
preparación", y decide "catálogo vs. fuera de carta" según si el body
trae `producto_id` o `nombre`+`precio`.

`numero_dia_pedido_activo` (endpoint 1) expone, para cualquier mesa
"ocupada" o "pagada", el `daily_number` del pedido activo asociado —
visible para cualquier mesero autenticado, no solo el dueño, porque
RF-13/RF-14 (spec) resolvieron que el número del día no es "contenido"
restringido. `null` si la mesa está libre, o si su pedido activo aún no
tiene número (caso transitorio, borrador recién creado). Es el único
campo de `GET /api/mesas` que identifica un pedido; el resto de su
contenido (ítems, notas, total) sigue sin exponerse ahí.

`numero_dia`/`enviado_en` (RF-14, sección 4.1) viajan como par en
cualquier respuesta que incluya un pedido (endpoints 3, 4, 5, 6, 11): el
entero crudo y el ISO datetime de `sent_at`, `null` los dos mientras el
pedido siga en "borrador". El formato de presentación ("N° 7") es
responsabilidad del frontend, no del contrato de API. El endpoint 11
(`enviar`) es el único que hace la transición real de `null` a su
primer valor — su respuesta 200 incluye el pedido completo, igual que
los demás endpoints que devuelven el pedido tras una acción (12, 13).
El campo `id` interno sigue presente en todas estas respuestas sin
excepción (RF-14 solo prohíbe mostrarlo como texto en pantalla, nunca
en el payload de la API — ver spec 003, RF-14).

Códigos de estado usados y su porqué:
- **400** — validación de campo (nombre/precio/nota/cantidad/motivo
  faltante o inválido), o número de mesas <1.
- **401** — sin sesión.
- **403** — rol incorrecto (mesero en acción de admin o viceversa), o
  mesero actuando sobre un pedido que no es suyo.
- **404** — recurso no existe.
- **409** — conflicto de estado: mesa no libre/ocupada/pagada según la
  acción, pedido cobrado/anulado, ítem ya anulado, producto no
  disponible.

---

## 4. Mecanismo de tiempo real

- `apps/orders/consumers.py` define `OrderConsumer` en `/ws/pedidos/`,
  agregado al `websocket_urlpatterns` que `config/asgi.py` ya expone
  desde 002-gestion-menu (mismo `AuthMiddlewareStack` +
  `ProtocolTypeRouter`, sin instalar nada nuevo).
- A diferencia de `MenuConsumer` (002, abierto a admin y mesero), este
  consumer solo acepta conexiones de **admin** — es el feed del panel
  `admin/pedidos`, el mesero no lo necesita (actúa siempre sobre pedidos
  propios que ya tiene en pantalla).
- Todos los admins conectados se unen a un único grupo, `"orders_admin"`
  (sección 5, decisión 5).
- `services.py` llama a `notify_orders_changed()` (mismo patrón "dumb"
  de invalidación que `notify_menu_changed()` en 002) después de: enviar
  un pedido (RF-5, primera vez que el admin debe enterarse — un borrador
  nunca notifica, todavía no hay compromiso hacia cocina), agregar una
  adición (RF-5), anular un ítem (RF-6), anular un pedido completo,
  manual o automático (RF-11). **No** notifica: crear el borrador,
  agregar/quitar ítems en borrador, cobrar (RF-9, el admin que cobra ya
  sabe que lo hizo — no necesita notificarse a sí mismo) ni marcar
  entregado/liberar mesa (acciones que no cambian qué debe cobrarse).
- El evento es `{"type": "pedidos.actualizado"}`, sin payload — el
  cliente admin, al recibirlo, vuelve a pedir
  `GET /api/pedidos/entrantes` completo (mismo patrón que 002).

### Pseudocódigo

```
FUNCTION enviar_pedido(pedido):
    SI pedido.estado != DRAFT:
        RETORNAR sin_cambios()          # RF-5: reenvío se ignora
    SI pedido.items.filter(is_voided=False).count() == 0:
        RECHAZAR 409("El pedido no tiene ningún ítem.")
    pedido.estado = IN_PROGRESS
    asignar_numero_del_dia(pedido)      # RF-14, ver sección 4.1 — dentro
                                         # de la misma transacción
    guardar(pedido)
    notificar_pedidos_actualizados()    # primera vez que el admin se entera
    RETORNAR 200(pedido)

FUNCTION anular_item(pedido, item, mesero, motivo):
    SI pedido.mesero != mesero:
        RECHAZAR 403()
    SI pedido.estado != IN_PROGRESS:
        RECHAZAR 409("Este pedido no admite anulación de ítems.")
    item.is_voided = True
    item.void_reason = motivo
    guardar(item)
    registrar_accion(pedido, ITEM_VOIDED, mesero, motivo, item=item)
    activos = pedido.items.filter(is_voided=False)
    SI activos.count() == 0:
        pedido.estado = VOIDED
        guardar(pedido)
        liberar_mesa_de(pedido)                     # vuelve a FREE
        registrar_accion(pedido, ORDER_VOIDED_AUTO, mesero, motivo)  # mismo mesero/motivo
    notificar_pedidos_actualizados()
    RETORNAR 200(pedido)
```

---

## 4.1. Asignación del número del día (RF-14)

**Opción A — Calcular el siguiente número contando filas** (ej.
`Order.objects.filter(sent_at__date=hoy).count() + 1`).

- A favor: no necesita una tabla nueva.
- En contra: es un patrón leer-luego-escribir clásico. Dos solicitudes
  de envío casi simultáneas pueden leer el mismo `count()` antes de que
  ninguna haya guardado todavía, y ambas calcularían el mismo "siguiente
  número" — exactamente la condición de carrera que RF-14 prohíbe. Ya se
  aprendió en este mismo proyecto (004, `kitchen_printing`) que
  envolver ambas lecturas en una sola `transaction.atomic()` no alcanza
  por sí solo: SQLite en modo *shared-cache* puede devolver
  `OperationalError: database table is locked` a la segunda escritura en
  vez de serializarla de forma transparente.

**Opción B — Un contador dedicado (`DailyOrderCounter`, sección 2) más
el mismo `threading.Lock()` en memoria que ya serializa la impresora en
`kitchen_printing` (004).**

- A favor: aplica la lección ya aprendida en 004 sin introducir un
  mecanismo nuevo — un único proceso Daphne/ASGI (regla 1, sin
  multi-worker) hace que un lock de proceso sea suficiente para
  garantizar que todo el ciclo "leer `last_number`, incrementarlo,
  guardarlo, asignarlo al pedido" ocurra de a una solicitud a la vez,
  sin depender de cómo SQLite resuelva escrituras concurrentes.
- En contra: ninguno relevante — es el mismo patrón que ya se validó en
  producción (004) para un problema de la misma forma (un recurso
  compartido que una sola solicitud a la vez puede tocar).

**Decisión: Opción B.** Mismo lock, mismo razonamiento que 004: más
simple y más robusto que confiar en el comportamiento de concurrencia
de SQLite para esta operación.

```
NUMERO_DEL_DIA_LOCK = threading.Lock()   # distinto del lock de 004 (otro recurso)

FUNCTION asignar_numero_del_dia(pedido):
    hoy = timezone.localdate()           # America/Bogota (regla 2)
    CON NUMERO_DEL_DIA_LOCK:
        contador, _ = DailyOrderCounter.objects.get_or_create(
            local_date=hoy, defaults={"last_number": 0}
        )
        contador.last_number += 1
        guardar(contador)
        pedido.daily_number = contador.last_number
        pedido.sent_at = timezone.now()
```

Esta función se llama **dentro** de la misma `transaction.atomic()` que
ya envuelve `enviar_pedido` (pseudocódigo de la sección 4): si el envío
falla por cualquier otra razón después de incrementar el contador, la
transacción completa se revierte — contador incluido — así que un fallo
a mitad de proceso no dejaría un hueco en la práctica; el único caso que
sí podría dejarlo es una caída del proceso entre el `COMMIT` confirmado
y antes de que la respuesta HTTP salga, fuera del control de esta
función (consistente con que la spec, RF-14, tolera huecos sin
exigir que el sistema los rellene).

`asignar_numero_del_dia` nunca se llama en ninguna otra transición de
estado (adición, anulación de ítem/pedido, corrección de mesa) — esas
rutas de `services.py` simplemente no la invocan, que es como RF-14
garantiza la inmutabilidad: no hay ninguna rama de código que vuelva a
tocar `daily_number`/`sent_at` una vez asignados.

---

## 5. Decisiones técnicas justificadas

1. **`Order.table_number` como entero copiado, no `ForeignKey` a
   `Table`.**
   Descartado: una FK viva a `Table`. Bajar el número de mesas (RF-1)
   elimina filas de `Table`; si `Order` la referenciara en vivo, el
   historial de pedidos de una mesa eliminada quedaría roto o forzaría
   `PROTECT` (que impediría eliminar mesas con historial, contradiciendo
   RF-1, que solo exige que la mesa esté *libre*, no que carezca de
   historial). Mismo razonamiento que 002-gestion-menu usó para no
   referenciar `Product` en vivo desde las líneas de pedido.

2. **Un solo endpoint para agregar ítems** (catálogo o fuera de carta,
   original o adición), en vez de cuatro endpoints separados.
   Descartado: `POST /items/catalogo`, `POST /items/fuera-de-carta`,
   `POST /items/adicion-catalogo`, `POST /items/adicion-fuera-de-carta`.
   Duplicaría la misma validación de "¿puedo editar este pedido ahora?"
   cuatro veces; el servidor ya sabe distinguir el origen del ítem por el
   payload y el tipo de línea por el estado del pedido.

3. **`OrderAction` como tabla de auditoría única** (mismo patrón que
   `AccountAction` en 001-autenticacion-usuarios) para anulación de
   ítem, anulación de pedido, corrección de mesa y cobro.
   Descartado: campos de auditoría repartidos por `Order`/`OrderItem`
   (ej. `voided_by`, `voided_at`, `table_changed_by` como columnas
   sueltas). Fragmentaría la trazabilidad de la regla 4 en varios
   lugares en vez de un único punto consultable — y es exactamente el
   campo de "historial de cambios de mesa" que pedía el prompt original,
   filtrando por `action_type=TABLE_CORRECTED`.

4. **Reutilizar el `ProtocolTypeRouter`/`AuthMiddlewareStack` ya
   configurados por 002-gestion-menu**, agregando solo una ruta más al
   mismo `websocket_urlpatterns`.
   Descartado: una segunda app ASGI o una nueva instalación de
   `channels`/`daphne`. Ya están en `requirements.txt` y configurados en
   `config/asgi.py`; duplicar esa infraestructura violaría la regla 1
   (stack mínimo).

5. **Un único grupo de Channels (`"orders_admin"`)** para el feed de
   pedidos entrantes, sin partición por mesa.
   Descartado: un grupo por mesa o por pedido. El panel admin necesita
   ver *todos* los pedidos entrantes a la vez para decidir qué cobrar;
   particionar por mesa solo añadiría complejidad de suscripción sin
   ningún beneficio a este alcance.

6. **`quantity` (cantidad) como campo entero en `OrderItem`**, en vez de
   forzar al mesero a repetir la misma línea N veces.
   Descartado: sin campo de cantidad, pedir "3 limonadas" exigiría tres
   líneas idénticas. Se documenta la consecuencia de este diseño: anular
   una línea (RF-6) anula toda su cantidad de una vez — no hay anulación
   parcial de una misma línea (ej. anular 1 de 3 limonadas exige que el
   mesero haya agregado esa limonada como una línea aparte desde el
   principio).

7. **Permiso de objeto `IsOrderOwner`** (`request.user == order.waiter`)
   reutilizable en cada vista, en vez de repetir la comprobación de
   dueño manualmente en cada endpoint.
   Descartado: `if request.user != order.waiter: return 403` copiado en
   cada vista. Una clase de permiso centralizada evita que alguna vista
   nueva olvide la comprobación.

8. **Sin locking optimista (campo de versión) para las carreras de
   concurrencia** — se resuelven revalidando el estado de la mesa/pedido
   dentro de la misma transacción de base de datos justo antes de
   aplicar el cambio.
   Descartado: un campo `version` con `select_for_update` explícito o
   una cola de eventos. La NFR de la spec ya define la regla como "gana
   la primera solicitud, la segunda se rechaza por precondición" —
   exactamente el comportamiento que ya producen las validaciones de
   estado que cada RF exige, sin infraestructura adicional (consistente
   con la regla 1, sin Redis).

9. **`threading.Lock()` en memoria del proceso + tabla
   `DailyOrderCounter`** para asignar el número del día (RF-14), en vez
   de contar filas de `Order` al vuelo — justificada en detalle en la
   sección 4.1 (mismo patrón que el lock de impresión de 004).

10. **La etiqueta visible "Entregado" (RF-8) se calcula en el frontend
    combinando `status` + `delivered`, en vez de agregar un quinto valor
    real a `Order.status`.**
    Descartado: un estado `DELIVERED` en la base de datos. Habría
    obligado a revisar y actualizar cada chequeo que hoy compara
    `order.status == IN_PROGRESS` para que también acepte el nuevo
    valor — `add_item`/`void_item`/`fix_table` en `services.py`,
    `charge_order` en `apps.payments.services` (005), `retry_print` en
    `apps.kitchen_printing.services` (004), y los 4 chequeos de
    `OrderBuilder.tsx` —, con el riesgo de romper algo ya probado para
    ganar nada a cambio: `delivered` ya viaja en todo payload de pedido,
    y `status` sigue siendo la única fuente de verdad para qué acciones
    proceden (RF-5, RF-6, RF-7, RF-9, RF-11). Calcular la etiqueta en
    `MyOrdersList.tsx`/`OrderBuilder.tsx` (las únicas dos pantallas que
    muestran el badge de estado al mesero) logra el mismo resultado
    visible sin tocar backend ni esos chequeos.

---

## 6. Estrategia de tests

Cumpliendo la regla 6 de la constitución (todo endpoint de API y toda
acción sensible tiene al menos un test).

### Unitarios (`Django TestCase`, sin HTTP — prueban `services.py` y
`models.py` en aislamiento)

- RF-1: subir el número de mesas crea mesas libres; bajarlo elimina
  desde la numeración más alta; rechazo si alguna a eliminar no está
  libre; rechazo por debajo de 1.
- RF-2: crear pedido exige mesa libre; garantiza un único pedido activo
  por mesa; quitar un ítem en "borrador" borra la línea sin motivo ni
  rastro.
- RF-3: ítem de catálogo copia nombre/precio (no se relee el producto
  después); ítem fuera de carta exige nombre/precio manual; sin
  unicidad de nombre fuera de carta; revalidación de disponibilidad al
  agregar.
- RF-4: nota opcional, límite de 200 caracteres, editable mientras el
  ítem y el pedido sigan activos.
- RF-5: enviar pasa borrador → en preparación; reenviar se ignora sin
  error; agregar ítem tras enviar se marca `ADDITION`; bloqueo de
  adiciones si cobrado o anulado.
- RF-6: anular un ítem exige motivo, no borra la línea, se excluye del
  total; rechazo si el pedido no es del mesero o ya no está en
  preparación; anulación automática del pedido completo (mismo
  mesero/motivo) al quedar sin ítems activos, con liberación de mesa.
- RF-7: corregir mesa exige mesa destino libre (incluida la misma mesa,
  que nunca está "libre" de sí misma); el dueño del pedido nunca cambia;
  rechazo si cobrado/anulado.
- RF-8: "entregado" se puede alternar en borrador/en preparación/cobrado;
  se rechaza en anulado.
- RF-9: cobrar cambia pedido→cobrado y mesa→pagada; rechazo si lo intenta
  un mesero, o si la mesa no está ocupada.
- RF-10: liberar solo si la mesa está pagada; lo puede hacer cualquier
  mesero.
- RF-11: anular pedido completo en borrador o en preparación; rechazo si
  ya cobrado; libera la mesa.
- RF-12: cada acción sensible (T anterior) deja exactamente una fila
  nueva en `OrderAction` con los datos esperados.
- RF-14: enviar un pedido en "borrador" le asigna `daily_number=1` y
  `sent_at` si es el primero del día; el segundo pedido enviado el mismo
  día recibe `2`; un pedido en otra fecha local (mockeando
  `DailyOrderCounter` con `local_date` de ayer) arranca de nuevo en `1`;
  reenviar un pedido ya "en preparación" no cambia ni vuelve a tocar su
  `daily_number`/`sent_at`; agregar una adición, anular un ítem, anular
  el pedido completo (manual o automático), o corregir la mesa, dejan
  `daily_number`/`sent_at` intactos; dos llamadas a
  `asignar_numero_del_dia` desde dos hilos distintos (simulando envíos
  casi simultáneos, mismo patrón que `PrintLockSerializationTests` de
  004) nunca producen el mismo número.

### Integración (`DRF APIClient`, HTTP real)

- Los 16 endpoints de la sección 3: status code y payload correctos para
  cada caso de éxito y de error (400/401/403/404/409) — cubre RF-1 a
  RF-13 uno a uno.
- RF-14: `POST /api/pedidos/{id}/enviar` devuelve `numero_dia`/
  `enviado_en` en su respuesta 200; `GET /api/pedidos/mios`,
  `/entrantes` y `/{id}` devuelven `numero_dia: null`/`enviado_en: null`
  mientras el pedido siga en "borrador", y los valores reales después de
  enviarlo; `GET /api/mesas` devuelve `numero_dia_pedido_activo` correcto
  para una mesa ocupada/pagada, y `null` para una libre — probado tanto
  con el mesero dueño del pedido como con uno ajeno (no es "contenido"
  restringido por RF-13), confirmando que el ajeno sigue recibiendo 403
  si intenta `GET /api/pedidos/{id}` de ese mismo pedido.
- Flujo completo: ajustar mesas → crear pedido → enviar → agregar
  adición → anular un ítem (verifica `OrderAction`) → corregir mesa →
  marcar entregado → cobrar → liberar mesa.
- RF-13: un mesero ajeno recibe 403 al pedir el contenido de un pedido
  que no es suyo, pero sí ve el estado de esa mesa en `GET /api/mesas`.
- Casos límite de mesas: bajar el número con una mesa ocupada en el
  rango a eliminar (409); bajar por debajo de 1 (400); dos meseros
  creando un pedido en la misma mesa libre casi al mismo tiempo (el
  segundo recibe 409).
- Indicador "Entregado" independiente: un test por cada estado principal
  (borrador, en preparación, cobrado) confirmando que se puede
  marcar/desmarcar, y uno confirmando el rechazo en "anulado".

### Canal en tiempo real (`channels.testing.WebsocketCommunicator`)

- Un admin conectado recibe `pedidos.actualizado` al enviar un pedido,
  agregar una adición, anular un ítem, y anular un pedido completo
  (manual o automático).
- Un mesero, o un cliente sin sesión válida, no puede conectarse al
  canal.
- Crear un pedido en borrador, o cobrar, o marcar entregado/liberar mesa,
  no dispara ningún evento (caso límite explícito de la sección 4).

### Frontend (fuera del alcance estricto de la regla 6, recomendado)

- `OrderBuilder`: el selector de producto del catálogo siempre viene de
  una lista (mismo patrón que 002), nunca texto libre, salvo en el modo
  explícito "fuera de carta".
- `IncomingOrdersPanel`: el botón "Actualizar" y la llegada de un evento
  por socket disparan el mismo refetch (mismo patrón que 002).

---

## Cobertura de requisitos funcionales

| RF | Cubierto en |
|----|--------------|
| RF-1 | Sección 2 (`Table`), Sección 3 (endpoints 1-2), Sección 6 |
| RF-2 | Sección 2 (`Order`), Sección 3 (endpoints 3, 8), pseudocódigo `enviar_pedido` (verificación previa) |
| RF-3 | Sección 2 (`OrderItem`), Sección 3 (endpoint 7), Decisión técnica 1 y 2 |
| RF-4 | Sección 2 (`OrderItem.note`), Sección 3 (endpoints 7, 10) |
| RF-5 | Sección 3 (endpoint 11), Sección 4 (cuándo notifica), pseudocódigo `enviar_pedido` |
| RF-6 | Sección 2 (`OrderAction`), Sección 3 (endpoint 9), Sección 4, pseudocódigo `anular_item`, Decisión técnica 3 |
| RF-7 | Sección 2 (`Order.table_number`, `OrderAction.from/to_table_number`), Sección 3 (endpoint 12), Decisión técnica 1 |
| RF-8 | Sección 2 (`Order.delivered`), Sección 3 (endpoint 13), Decisión técnica 10 (etiqueta visible "Entregado" calculada en el frontend) |
| RF-9 | Sección 3 (endpoints 5, 14) |
| RF-10 | Sección 3 (endpoint 16) |
| RF-11 | Sección 2 (`OrderAction.ORDER_VOIDED`/`ORDER_VOIDED_AUTO`), Sección 3 (endpoint 15), pseudocódigo `anular_item` (rama automática) |
| RF-12 | Sección 2 (`OrderAction`), todas las funciones de servicio en sección 4/5 que llaman `registrar_accion` |
| RF-13 | Sección 1 (`permissions.py`, `IsOrderOwner`), Sección 3 (endpoints 4-6, columna Auth), Sección 4 (consumer admin-only) |
| RF-15 | Sección 3 (endpoints 17-18 y nota de RF-15 debajo de la tabla), Sección 6 |
| RF-16 | Sección 3 (endpoint 4, `?fecha=`) |
| RF-17 | Sección 3 (endpoint 19; `AdminOrderSerializer` agrega `admin_note` solo en las respuestas de vistas de admin) |
| RF-14 | Sección 2 (`Order.daily_number`/`sent_at`, `DailyOrderCounter`), Sección 3 (endpoint 1 `numero_dia_pedido_activo`, endpoints 3-6 y 11 `numero_dia`/`enviado_en`), Sección 4.1 (mecanismo de asignación, pseudocódigo), Decisión técnica 9, Sección 6 |
