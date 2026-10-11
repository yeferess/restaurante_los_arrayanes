# 005 · Cobro — Tareas

Basado en `spec.md` (requisitos) y `plan.md` (diseño técnico). Cada tarea
es de ~20-30 min, están en orden de dependencia (no empezar una tarea sin
que las anteriores estén hechas). Cada una indica el/los RF que cubre y
una condición verificable de "Hecho cuando".

---

## Fase 0 — Setup del módulo

- [x] **T01 — Crear la app `payments`**
  RF: — (infraestructura)
  Hecho cuando: existe `apps/payments/` con la estructura del plan
  (sección 1), está en `INSTALLED_APPS`, y `python manage.py check` no
  reporta errores.

- [x] **T02 — Registrar `urls.py` del módulo**
  RF: — (infraestructura)
  Hecho cuando: `config/urls.py` incluye `apps.payments.urls` bajo
  `/api/`, y una request a una ruta aún no implementada devuelve 404
  (no 500 ni error de importación).

---

## Fase 1 — Modelo de datos

- [x] **T03 — Modelo `PaymentAccount`**
  RF: RF-2
  Hecho cuando: existe el modelo con `name` (`CharField`, `unique=True`,
  no vacío), `is_fixed` (`BooleanField`, default `False`), `created_at`,
  y la migración aplica sin errores.

- [x] **T04 — Data migration: sembrar la cuenta fija "Efectivo"**
  RF: RF-2
  Hecho cuando: al correr `migrate` desde cero, existe exactamente una
  fila `PaymentAccount` con `name="Efectivo"` e `is_fixed=True`, sin
  necesitar ningún paso manual.

- [x] **T05 — Modelo `Payment` con `UniqueConstraint` condicional**
  RF: RF-3, RF-6, RF-7
  Hecho cuando: existe el modelo con `order` (FK `PROTECT`), `account`
  (FK `PROTECT`), `amount` (`DecimalField`), `status` (choices
  `ACTIVE`/`VOIDED`, default `ACTIVE`), `charged_by`, `charged_at`,
  `voided_by`, `voided_at`, `void_reason`; la migración aplica sin
  errores; un test confirma que crear un segundo `Payment` `ACTIVE`
  para el mismo `order` lanza `IntegrityError`
  (`unique_active_payment_per_order`), mientras que un segundo
  `Payment` `VOIDED` para el mismo `order` sí se puede crear.

---

## Fase 2 — Servicios: catálogo de cuentas

- [x] **T06 — `create_account()`**
  RF: RF-2
  Hecho cuando: crea una `PaymentAccount` nueva con el nombre dado;
  rechaza un nombre vacío; rechaza un nombre ya usado por otra cuenta
  (incluyendo "Efectivo").

- [x] **T07 — `delete_account()`**
  RF: RF-2
  Hecho cuando: elimina una cuenta sin ningún `Payment` asociado;
  rechaza eliminar la cuenta con `is_fixed=True`; rechaza eliminar una
  cuenta con al menos un `Payment` asociado (activo o anulado).

---

## Fase 3 — Servicios: registrar un cobro

- [x] **T08 — `charge_order()`: validaciones y monto**
  RF: RF-1, RF-4
  Hecho cuando: rechaza cobrar un pedido en "borrador", ya "cobrado" o
  "anulado"; rechaza si la mesa del pedido no está "ocupada"; calcula
  el monto como la suma de los ítems activos (cantidad × precio,
  excluyendo los anulados) — mismo cálculo que
  `OrderSerializer.get_total`.

- [x] **T09 — `charge_order()`: crear el cobro y aplicar sus efectos**
  RF: RF-3, RF-5
  Hecho cuando: con una opción de pago válida, crea un `Payment`
  `ACTIVE` con el monto calculado (T08), el admin y la fecha/hora;
  cambia el pedido a "cobrado" y la mesa a "pagada" (sin liberarla);
  registra la traza (`OrderAction.ActionType.CHARGED`), igual que el
  `charge_order` original de 003.

- [x] **T10 — `charge_order()`: condición de carrera**
  RF: RF-1, RF-7
  Hecho cuando: un test simula dos llamadas a `charge_order` para el
  mismo pedido (la segunda antes de que la primera cambie el estado
  del pedido) y confirma que la segunda recibe el error "este pedido ya
  fue cobrado" en vez de crear un segundo `Payment` `ACTIVE` — apoyado
  en la restricción de la base de datos (T05), no en un lock de
  aplicación.

---

## Fase 4 — Servicios: corrección de un cobro

- [x] **T11 — `void_charge()`: validaciones**
  RF: RF-6
  Hecho cuando: rechaza si el pedido no tiene ningún `Payment`
  `ACTIVE`; rechaza si se intenta anular un `Payment` que ya está
  `VOIDED`; exige un `reason` no vacío.

- [x] **T12 — `void_charge()`: bloqueo por mesa reasignada**
  RF: RF-6
  Hecho cuando: si la mesa del pedido ya tiene otro pedido distinto en
  estado "borrador" o "en preparación", la anulación se rechaza y el
  `Payment` original queda intacto (sigue `ACTIVE`).

- [x] **T13 — `void_charge()`: efectos de una anulación exitosa**
  RF: RF-6
  Hecho cuando: si la mesa no tiene otro pedido activo, marca el
  `Payment` como `VOIDED` (con `voided_by`, `voided_at`, `void_reason`)
  sin modificar ninguno de sus demás campos; el pedido vuelve a "en
  preparación"; la mesa vuelve a "ocupada" solo si seguía "pagada" (si
  ya estaba "libre", no se toca); se llama a `notify_orders_changed()`.

---

## Fase 5 — Integración con `apps.orders`

- [x] **T14 — Reemplazar el `charge_order` de 003**
  RF: RF-1, RF-3, RF-5
  Hecho cuando: se elimina `charge_order(order, admin)` de
  `apps/orders/services.py`; `ChargeOrderView` (en
  `apps/orders/views.py`) llama en su lugar a
  `apps.payments.services.charge_order(order, admin, account)`; los
  tests de 003 que cubrían el `charge_order` viejo se actualizan o se
  mueven a `apps.payments` según corresponda, y la suite completa del
  backend sigue en verde.

---

## Fase 6 — Endpoints y contrato de API

- [x] **T15 — Extender `POST /api/pedidos/{id}/cobrar`**
  RF: RF-1, RF-3, RF-5, RF-8
  Hecho cuando: el endpoint exige `account_id` en el body (400 si
  falta o la cuenta no existe); responde 200 con el pedido y
  `active_payment`; responde 409 en los casos de T08/T10; solo un
  admin puede llamarlo (403 para cualquier otro rol, 401 sin sesión).

- [x] **T16 — `POST /api/pedidos/{id}/cobro/anular`**
  RF: RF-6, RF-8
  Hecho cuando: exige `reason` en el body (400 si falta); responde 200
  con el pedido (`active_payment: null`) si la anulación procede; 404
  si no hay cobro activo; 409 si la mesa ya fue reasignada o el cobro
  ya estaba anulado; solo un admin puede llamarlo.

- [x] **T17 — `GET`/`POST /api/cuentas-pago`**
  RF: RF-2, RF-8
  Hecho cuando: `GET` devuelve la lista completa del catálogo
  (incluida "Efectivo"); `POST` crea una cuenta nueva (201) o rechaza
  nombre vacío/duplicado (400/409); ambos exigen rol admin.

- [x] **T18 — `DELETE /api/cuentas-pago/{id}`**
  RF: RF-2, RF-8
  Hecho cuando: elimina una cuenta sin uso (204); rechaza "Efectivo" o
  una cuenta ya usada (409); rechaza una cuenta inexistente (404);
  exige rol admin.

- [x] **T19 — `active_payment` en las lecturas de pedidos**
  RF: RF-3, RF-7
  Hecho cuando: `GET /api/pedidos/mios`, `/entrantes` y `/{id}`
  incluyen `active_payment` (`null`, o los datos del `Payment` `ACTIVE`
  vigente: cuenta, monto, quién y cuándo cobró).

---

## Fase 7 — Tiempo real

- [x] **T20 — Notificación en tiempo real al anular un cobro**
  RF: RF-6
  Hecho cuando: un admin conectado a `/ws/pedidos/` recibe
  `pedidos.actualizado` cuando una anulación de cobro tiene éxito; no
  lo recibe cuando se rechaza (T11/T12); cobrar (como ya pasaba en 003)
  sigue sin notificar.

---

## Fase 8 — Tests de integración

- [x] **T21 — Integration tests del endpoint de cobrar (T15)**
  RF: RF-1, RF-3, RF-5
  Hecho cuando: cada código de respuesta (200 éxito, 400, 403, 409
  — incluida la condición de carrera) tiene al menos un test, y todos
  pasan.

- [x] **T22 — Integration tests del endpoint de anular cobro (T16)**
  RF: RF-6
  Hecho cuando: cada código de respuesta (200, 400, 403, 404, 409 —
  mesa reasignada y cobro ya anulado) tiene al menos un test, y todos
  pasan.

- [x] **T23 — Integration tests del catálogo de cuentas (T17, T18)**
  RF: RF-2
  Hecho cuando: cada código de respuesta de ambos endpoints tiene al
  menos un test, y todos pasan.

- [x] **T24 — Integration test: ciclo completo cobrar → anular → recobrar**
  RF: RF-6, RF-7
  Hecho cuando: un test reproduce cobrar un pedido con "Efectivo" →
  anular ese cobro con un motivo → volver a cobrarlo con otra cuenta →
  confirma que existen dos `Payment` (uno `VOIDED` intacto, uno
  `ACTIVE`) y que el pedido queda "cobrado" con el segundo.

---

## Fase 9 — Frontend

- [x] **T25 — `lib/api/payments.ts`**
  RF: RF-2, RF-6
  Hecho cuando: existen `listAccounts()`, `createAccount(name)`,
  `deleteAccount(id)` y `voidCharge(orderId, reason)`, cada una
  llamando al endpoint correspondiente y propagando el error de la API
  tal cual.

- [x] **T26 — `chargeOrder()` y el tipo `Order` en `lib/api/orders.ts`**
  RF: RF-1, RF-3
  Hecho cuando: `chargeOrder(orderId, accountId)` envía `account_id` en
  el body; el tipo `Order` gana `active_payment: PaymentSummary | null`.

- [x] **T27 — `ChargeOrderModal.tsx`**
  RF: RF-1, RF-3, RF-4
  Hecho cuando: muestra el total del pedido (ya calculado) y una lista
  desplegable con las cuentas de `listAccounts()`; al confirmar llama a
  `chargeOrder`; muestra el error tal cual si la API lo rechaza (400/409).

- [x] **T28 — Botón "Cobrar" abre el modal en "Pedidos entrantes"**
  RF: RF-1
  Hecho cuando: `IncomingOrdersPanel.tsx` abre `ChargeOrderModal` al
  tocar "Cobrar" en vez de cobrar directo; al confirmar, refresca la
  lista y el pedido cobrado deja de aparecer como pendiente de cobro.

- [x] **T29 — Indicador y botón "Anular cobro"**
  RF: RF-6
  Hecho cuando: un pedido "cobrado" muestra con qué cuenta se pagó
  (`active_payment`) y un botón "Anular cobro" que pide un motivo
  (`window.prompt`, mismo patrón que "Anular pedido" de 003) y llama a
  `voidCharge`; si la API lo rechaza, muestra el mensaje de error tal
  cual.

- [x] **T30 — `PaymentAccountsManagement.tsx`**
  RF: RF-2
  Hecho cuando: lista las cuentas del catálogo ("Efectivo" sin botón de
  eliminar), permite crear una cuenta nueva con un nombre, y permite
  eliminar una cuenta sin uso; muestra el error tal cual si la API
  rechaza la eliminación de una cuenta ya usada.

---

## Fase 10 — Número del día (RF-4, 003-RF-14)

- [x] **T31 — `ChargeOrderModal.tsx` muestra el número del día**
  RF: RF-4, 003-RF-14
  Hecho cuando: el modal de cobro muestra "N° {numero_dia}" en vez de
  "Pedido #{id}" en su encabezado, con la fecha/hora de envío
  (`enviado_en`) en menor jerarquía visual debajo; con un pedido sin
  número del día (`numero_dia: null`, enviado antes de este cambio),
  ese campo se muestra en blanco sin romper el modal ni bloquear el
  cobro.

- [x] **T32 — Verificar que el indicador de cobro no usa el id interno**
  RF: RF-4, 003-RF-14
  Hecho cuando: ningún texto visible del panel de "Pedidos entrantes" ni
  del indicador "con qué cuenta se pagó" (`active_payment`) usa
  `order.id`; ambos identifican el pedido por `numero_dia`, igual que ya
  hace `MyOrdersList`/`IncomingOrdersPanel` de 003 (T80).

- [x] **T33 — Pestaña "Cobrados" del admin**
  RF: RF-9
  Hecho cuando: `GET /api/pedidos/cobrados` lista solo pedidos cobrados
  de la fecha pedida (hoy por defecto), más reciente primero, con
  `waiter_username` y `active_payment`; rechaza fecha mal formada (400)
  y a meseros (403); `ChargedOrdersPanel` en `/admin/pedidos/cobrados`
  con selector de fecha, detalle y botón "Reimprimir". Tests en
  `test_charged_orders.py` y `ChargedOrdersPanel.test.tsx`.
