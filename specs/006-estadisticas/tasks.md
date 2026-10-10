# 006 · Estadísticas — Tareas

Basado en `spec.md` (requisitos) y `plan.md` (diseño técnico). Cada tarea
es de ~20-30 min, están en orden de dependencia (no empezar una tarea sin
que las anteriores estén hechas). Cada una indica el/los RF que cubre y una
condición verificable de "Hecho cuando".

---

## Fase 0 — Setup del módulo

- [x] **T01 — Crear la app `stats`**
  RF: — (infraestructura)
  Hecho cuando: existe `apps/stats/` con la estructura de `plan.md`
  (sección 1) — sin `models.py` ni migraciones —, está en
  `INSTALLED_APPS`, y `python manage.py check` no reporta errores.

- [x] **T02 — Registrar `urls.py` del módulo**
  RF: — (infraestructura)
  Hecho cuando: `config/urls.py` incluye `apps.stats.urls` bajo `/api/`,
  y una request a `/api/estadisticas/resumen` sin sesión devuelve 401
  (no 404 ni error de importación).

---

## Fase 1 — Servicios: dinero (RF-1, RF-2, RF-5, RF-10)

- [x] **T03 — `_qualifying_payments()`: estabilidad de días cerrados**
  RF: RF-10
  Hecho cuando: dado un rango de fechas, devuelve los `Payment` cuyo
  `charged_at` (fecha local) cae en el rango y que siguen `ACTIVE`, o
  que se anularon en una fecha **posterior** a su propio `charged_at`;
  excluye los anulados el mismo día en que se cobraron.

- [x] **T04 — `money_total()` y `orders_charged_count()`**
  RF: RF-1
  Hecho cuando: suman/cuentan únicamente sobre `_qualifying_payments()`
  (T03); `orders_charged_count` cuenta pedidos distintos (`order_id`
  único), no filas de `Payment` — un pedido anulado y vuelto a cobrar
  el mismo día cuenta una sola vez.

- [x] **T05 — `money_by_account()`**
  RF: RF-2
  Hecho cuando: desglosa `_qualifying_payments()` (T03) por
  `account__name`, ordenado de mayor a menor; la suma del desglose
  coincide siempre con `money_total()` (T04) del mismo rango; una
  cuenta sin cobros calificados en el rango no aparece.

---

## Fase 2 — Servicios: pedidos y productos (RF-3, RF-4, RF-5)

- [x] **T06 — `orders_sent_count()` y `orders_by_waiter()`**
  RF: RF-3
  Hecho cuando: cuentan/desglosan pedidos por `sent_at` (fecha local)
  dentro del rango, sin filtrar por `status` (un pedido en preparación,
  cobrado, o anulado por completo cuenta igual); un pedido en
  "borrador" (sin `sent_at`) nunca cuenta; un mesero sin pedidos en el
  rango no aparece en `orders_by_waiter`.

- [x] **T07 — `top_products()`**
  RF: RF-4
  Hecho cuando: cuenta unidades de `OrderItem` con `sent_at` del pedido
  dentro del rango, `is_voided=False`, `catalog_product` no nulo, y
  `order.status != VOIDED`; una adición agregada días después del
  envío original se atribuye igual al rango del `sent_at` del pedido;
  devuelve como máximo 10, ordenados de mayor a menor cantidad.

---

## Fase 3 — Servicios: resumen combinado y movimiento del día (RF-1 a RF-6)

- [x] **T08 — `day_summary()` y `range_summary()`**
  RF: RF-1, RF-2, RF-3, RF-4, RF-5
  Hecho cuando: ambas funciones combinan `money_total`/
  `orders_charged_count` (T04), `money_by_account` (T05),
  `orders_by_waiter` (T06) y `top_products` (T07) para un mismo rango;
  `day_summary(date)` es el caso particular `range_summary(date, date)`;
  una fecha `to` futura en `range_summary` no produce error, solo
  ausencia de datos para esos días.

- [x] **T09 — `day_movement()`**
  RF: RF-6
  Hecho cuando: devuelve la lista de pedidos con `sent_at` ese día
  (número del día, mesero, estado actual, total **actual** del pedido)
  y la lista de cobros con `charged_at` ese día (cuenta, monto, admin,
  estado activo/anulado); incluye pedidos y cobros anulados, para
  trazabilidad; un cobro anulado un día distinto al de su registro
  aparece solo en el movimiento de su `charged_at` original; un día sin
  movimiento devuelve ambas listas vacías.

---

## Fase 4 — Endpoints y permisos (RF-7, RF-8, RF-9)

- [x] **T10 — Permisos: reutilizar `IsAdmin`**
  RF: RF-8
  Hecho cuando: `apps/stats/permissions.py` reexporta `IsAdmin` de
  `apps.orders.permissions`.

- [x] **T11 — `GET /api/estadisticas/resumen`**
  RF: RF-1, RF-2, RF-3, RF-4, RF-8
  Hecho cuando: un admin recibe 200 con el resumen de `date` (default
  hoy) usando `day_summary()` (T08); `date` inválida devuelve 400; un
  mesero recibe 403; sin sesión, 401; la respuesta nunca incluye el id
  interno de ningún pedido (RF-7).

- [x] **T12 — `GET /api/estadisticas/rango`**
  RF: RF-5, RF-8
  Hecho cuando: un admin recibe 200 con `range_summary(from, to)`
  (T08); falta `from`/`to`, formato inválido, o `from` > `to` devuelve
  400; un mesero recibe 403; sin sesión, 401.

- [x] **T13 — `GET /api/estadisticas/movimiento`**
  RF: RF-6, RF-7, RF-8
  Hecho cuando: un admin recibe 200 con `day_movement(date)` (T09)
  (default hoy); `date` inválida devuelve 400; un mesero recibe 403;
  sin sesión, 401; cada pedido se identifica por `daily_number`, nunca
  por su id interno.

---

## Fase 5 — Tests

- [x] **T14 — Unit tests de estabilidad de días cerrados (T03)**
  RF: RF-10
  Hecho cuando: cubren un cobro anulado el día siguiente a su registro
  (no cambia el total ya calculado del día original), un cobro anulado
  el mismo día (se excluye igual que hoy), y que consultar el mismo día
  antes y después de una anulación tardía da el mismo resultado; todos
  pasan.

- [x] **T15 — Unit tests de dinero del día y por cuenta (T04, T05)**
  RF: RF-1, RF-2
  Hecho cuando: cubren el total y el conteo de pedidos distintos con
  varios cobros activos y uno anulado, el recobro el mismo día
  contando una sola vez, el desglose por cuenta, y que una cuenta sin
  cobros no aparece; todos pasan.

- [x] **T16 — Unit tests de pedidos por mesero (T06)**
  RF: RF-3
  Hecho cuando: cubren el conteo por `sent_at` sin importar el estado
  final del pedido, la exclusión de pedidos en "borrador", y que un
  mesero sin pedidos no aparece; todos pasan.

- [x] **T17 — Unit tests de productos más vendidos (T07)**
  RF: RF-4
  Hecho cuando: cubren la exclusión de ítems fuera de carta, ítems
  anulados, ítems de un pedido anulado por completo, la atribución de
  una adición tardía al día de envío original, la desaparición de un
  producto eliminado del catálogo, y el recorte a 10; todos pasan.

- [x] **T18 — Unit tests de movimiento del día (T09)**
  RF: RF-6
  Hecho cuando: cubren la inclusión de pedidos/cobros anulados, un
  cobro anulado un día distinto al de su registro apareciendo solo en
  el día original, y un día sin movimiento devolviendo listas vacías;
  todos pasan.

- [x] **T19 — Integration tests de los 3 endpoints (T11-T13)**
  RF: RF-1 a RF-6
  Hecho cuando: cada código de respuesta (200, 400, 401, 403) de los
  tres endpoints tiene al menos un test, y todos pasan.

- [x] **T20 — Integration tests de permisos (RF-8)**
  RF: RF-8
  Hecho cuando: los tres endpoints tienen un test que confirma 403 para
  un mesero autenticado y 401 sin sesión.

- [x] **T21 — Integration test: flujo completo**
  RF: RF-1, RF-2, RF-3, RF-4, RF-6
  Hecho cuando: un test end-to-end reproduce: crear pedido → enviarlo →
  agregar un ítem de catálogo → cobrarlo con una cuenta → confirmar que
  aparece correctamente en `/resumen`, `/rango` (que cubre ese día) y
  `/movimiento` de ese día, identificado por su número del día.

---

## Fase 6 — Frontend

- [x] **T22 — `lib/api/stats.ts`**
  RF: RF-1 a RF-6
  Hecho cuando: expone `getDaySummary(date?)`, `getRangeSummary(from,
  to)` y `getDayMovement(date?)`, cada una llamando al endpoint
  correspondiente y propagando el error tal cual lo devuelve la API.

- [x] **T23 — Pantalla `admin/estadisticas` — resumen del día**
  RF: RF-1, RF-2, RF-3, RF-4
  Hecho cuando: muestra, por defecto para hoy, el dinero total, el
  desglose por cuenta de pago, los pedidos por mesero, y los productos
  más vendidos, usando `getDaySummary()`.

- [x] **T24 — Filtro por rango de fechas (RF-5)**
  RF: RF-5
  Hecho cuando: permite elegir "desde"/"hasta" y muestra el mismo
  resumen (dinero, cuentas, meseros, productos) para ese rango usando
  `getRangeSummary()`; refleja el error 400 de `from` > `to` en la UI.

- [x] **T25 — Vista de movimiento de un día específico (RF-6)**
  RF: RF-6
  Hecho cuando: permite elegir cualquier día pasado y muestra la lista
  de pedidos (número del día, mesero, estado, total) y de cobros
  (cuenta, monto, admin, estado) de ese día, incluidos los anulados,
  usando `getDayMovement()`.

- [x] **T26 — Enlace "Estadísticas" en el panel admin**
  RF: — (navegación)
  Hecho cuando: `AdminShell.tsx` agrega una entrada propia (sin
  agrupar, mismo patrón que "Mesas" y "Pedidos") con
  `{ href: "/admin/estadisticas", label: "Estadísticas" }`.
