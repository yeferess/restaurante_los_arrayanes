# 005 · Cobro — Plan técnico

Este plan traduce a diseño técnico (el "cómo") la especificación
aprobada en `spec.md` (el "qué/por qué"). No contiene código, solo
estructura, contratos, pseudocódigo y decisiones justificadas.

## Cumplimiento de `docs/constitution.md`

- **Regla 1 (stack mínimo)**: no se suma ninguna dependencia ni
  infraestructura nueva — dos tablas más en la misma SQLite, resueltas
  con el ORM de Django y sus propias restricciones de integridad; nada
  de Redis, colas externas ni microservicios.
- **Regla 2 (offline-first en LAN)**: cobrar es una escritura local a la
  base de datos del propio equipo — no depende de la red del
  restaurante ni de internet.
- **Regla 3 (contrato de API)**: el frontend nunca calcula el total ni
  decide si un cobro es válido — solo consume los endpoints/campos de
  la sección 6.
- **Regla 4 (trazabilidad)**: ya ampliada por la spec — cobrar y
  gestionar el catálogo de cuentas registran quién y cuándo; anular un
  cobro se suma al grupo que además exige un motivo (por qué).
  `Payment`/`PaymentAccount` (sección 2) son append-only por diseño: no
  existe ninguna ruta de `UPDATE`/`DELETE` sobre un registro de cobro.
- **Regla 5 (permisos por rol)**: ya ampliada por la spec — "anula un
  cobro" y "gestiona el catálogo de cuentas de pago" se suman a las
  acciones exclusivas de admin, junto con "cobra" que ya existía.
- **Regla 6 (tests obligatorios)**: sección 8 cubre modelos, servicios
  (casos de éxito y de rechazo) e integración HTTP para cada endpoint
  nuevo o extendido.
- **Regla 7 (idioma)**: nombres de clases/campos/variables en inglés en
  el código real (`Payment`, `PaymentAccount`, `charge_order`,
  `void_charge`, etc.); este documento permanece en español.

---

## 1. Estructura de módulos/archivos

### Backend (`/backend`)

```
backend/
  apps/
    payments/                      # app dedicada (RF-1..RF-8), separada
                                    # de apps.orders a propósito
      models.py                    # PaymentAccount, Payment (sección 2)
      services.py                  # charge_order(...), void_charge(...),
                                    # create_account(...), delete_account(...)
      permissions.py               # reexporta IsAdmin de apps.orders
      serializers.py               # PaymentAccountSerializer, PaymentSerializer
      views.py                     # endpoints nuevos (sección 6)
      urls.py                      # incluido en config/urls.py bajo /api/
      apps.py
      migrations/
        0001_initial.py            # crea PaymentAccount y Payment
        0002_seed_efectivo.py      # data migration: fila fija "Efectivo"
      tests/
        test_models.py
        test_services_charge.py
        test_services_void_charge.py
        test_services_accounts.py
        test_views_charge.py
        test_views_void_charge.py
        test_views_accounts.py
        test_integration_recharge_cycle.py
```

`apps/orders/services.py` (ya existente, de 003) se modifica de forma
mínima: se **elimina** su función `charge_order(order, admin)` (RF-9 de
003 queda ahora implementada aquí, en `apps.payments`, con la opción de
pago agregada); nada más de ese archivo cambia.

`apps/orders/views.py`: `ChargeOrderView` deja de llamar a
`services.charge_order(order, admin)` y pasa a llamar a
`apps.payments.services.charge_order(order, admin, account)` — mismo
endpoint `POST /api/pedidos/{id}/cobrar` de siempre (sección 6), ahora
exige el campo `account_id` en el body.

`apps.orders` no importa nada más de `apps.payments`; `apps.payments`
sí importa de `apps.orders` (`Order`, `Table`, `register_action`,
`notify_orders_changed`) — misma dirección de dependencia que ya
estableció 004 con `apps.kitchen_printing`.

### Frontend (`/frontend`, Next.js App Router)

```
frontend/
  lib/api/
    payments.ts                  # nuevo: listAccounts(), createAccount(name),
                                  #   deleteAccount(id), voidCharge(orderId, reason)
    orders.ts                    # chargeOrder(orderId, accountId): Promise<Order>
                                  #   (ahora exige accountId); type Order gana
                                  #   active_payment: PaymentSummary | null
  components/
    ChargeOrderModal.tsx         # nuevo: modal de cobro — total + lista
                                  #   desplegable de opciones + confirmar
    PaymentAccountsManagement.tsx # nuevo: panel admin — crear/listar/
                                  #   eliminar cuentas del catálogo
    IncomingOrdersPanel.tsx       # el botón "Cobrar" abre ChargeOrderModal
                                  #   en vez de cobrar directo; + botón
                                  #   "Anular cobro" cuando el pedido está
                                  #   "cobrado" y se muestra su historial
```

No se toca `MyOrdersList.tsx` ni `OrderBuilder.tsx` del lado del
mesero — este módulo es enteramente del panel de admin (RF-8).

---

## 2. Modelo de datos

Dos tablas nuevas. Ninguna de las dos se edita ni se borra una vez
creada/usada (constitución, regla 4) — toda corrección es un registro
nuevo.

### Tabla `PaymentAccount` (catálogo de opciones de pago — RF-2)

| Campo        | Tipo                                  | Restricciones                                                  | RF   |
|--------------|----------------------------------------|-----------------------------------------------------------------|------|
| `id`         | `AutoField`                            | PK                                                                | —    |
| `name`       | `CharField(max_length=100)`            | `unique=True`, no vacío                                          | RF-2 |
| `is_fixed`   | `BooleanField`                         | default `False`; `True` solo en la fila "Efectivo"               | RF-2 |
| `created_at` | `DateTimeField(auto_now_add=True)`     | —                                                                  | —    |

La fila "Efectivo" (`is_fixed=True`) se siembra con una **data
migration** (`0002_seed_efectivo.py`), no con código de aplicación —
así existe desde el primer `migrate`, igual para todo despliegue.
`services.py` rechaza crear o eliminar cualquier fila con
`is_fixed=True`, y rechaza eliminar cualquier cuenta con al menos un
`Payment` asociado (activo o anulado) — ver sección 5.

### Tabla `Payment` (registro de cobro — RF-3, RF-6, RF-7)

| Campo         | Tipo                                                          | Restricciones                                                   | RF        |
|----------------|---------------------------------------------------------------|--------------------------------------------------------------------|-----------|
| `id`           | `AutoField`                                                    | PK                                                                    | —         |
| `order`        | `ForeignKey(Order, on_delete=PROTECT, related_name="payments")`| —                                                                     | RF-3, RF-7|
| `account`      | `ForeignKey(PaymentAccount, on_delete=PROTECT, related_name="payments")` | —                                                       | RF-2, RF-3|
| `amount`       | `DecimalField(max_digits=10, decimal_places=2)`                | snapshot del total del pedido en el momento de cobrar (RF-3, RF-4)   | RF-3      |
| `status`       | `CharField` choices `ACTIVE` / `VOIDED`                        | default `ACTIVE`                                                     | RF-6, RF-7|
| `charged_by`   | `ForeignKey(User, on_delete=PROTECT, related_name="payments_charged")`   | admin que registró el cobro                                | RF-3      |
| `charged_at`   | `DateTimeField(auto_now_add=True)`                              | —                                                                     | RF-3      |
| `voided_by`    | `ForeignKey(User, null=True, blank=True, on_delete=PROTECT, related_name="payments_voided")` | solo si `status=VOIDED`                      | RF-6      |
| `voided_at`    | `DateTimeField(null=True, blank=True)`                          | solo si `status=VOIDED`                                               | RF-6      |
| `void_reason`  | `CharField(max_length=200, blank=True)`                         | obligatorio en el servicio cuando se anula (RF-6)                     | RF-6      |

**Restricción de base de datos** que mantiene el invariante de RF-7 ("a
lo sumo un cobro activo por pedido") y resuelve la condición de carrera
de RF-1 — ver decisión técnica en la sección 4:

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["order"],
            condition=models.Q(status="ACTIVE"),
            name="unique_active_payment_per_order",
        )
    ]
```

`order.waiter` ya identifica al mesero dueño de la venta (RF-3) — no
hace falta un campo `waiter` propio en `Payment`.

**Ejemplo de registro** (cobro anulado por error, seguido de uno
activo — mismo pedido):

```json
[
  {
    "id": 11,
    "order_id": 41,
    "account_id": 1,
    "amount": "32.50",
    "status": "VOIDED",
    "charged_by_id": 2,
    "charged_at": "2026-03-10T20:40:00Z",
    "voided_by_id": 3,
    "voided_at": "2026-03-10T20:41:30Z",
    "void_reason": "Se eligió la cuenta equivocada"
  },
  {
    "id": 12,
    "order_id": 41,
    "account_id": 4,
    "amount": "32.50",
    "status": "ACTIVE",
    "charged_by_id": 3,
    "charged_at": "2026-03-10T20:42:00Z",
    "voided_by_id": null,
    "voided_at": null,
    "void_reason": ""
  }
]
```

---

## 3. Diseño de la pantalla de cobro y del catálogo de cuentas

No hay papel que diseñar (a diferencia de 004) — esto es una interfaz
web. Dos vistas nuevas, ambas dentro del panel de admin.

### Modal de cobro (se abre desde "Pedidos entrantes", botón "Cobrar")

```
┌─────────────────────────────────────┐
│  Cobrar N° 7 — Mesa 5                │
│  Enviado 10/03 20:15                 │ ← menor jerarquía visual (003-RF-14)
├─────────────────────────────────────┤
│  2x Limonada natural         $9.00   │
│  1x Sancocho de gallina      $20.00  │
│  1x Jugo de naranja          $5.00   │
│  ───────────────────────────────     │
│  Total                      $34.00   │ ← mismo total de 003 (RF-4)
│                                       │
│  Opción de pago                      │
│  [ Efectivo              ▾ ]         │ ← lista de PaymentAccount (RF-2)
│                                       │
│          [ Cancelar ]  [ Cobrar ]    │
└─────────────────────────────────────┘
```

`N° 7` y `Enviado 10/03 20:15` no son campos propios de este módulo:
vienen del `numero_dia`/`enviado_en` que 003 (RF-14, plan sección 3) ya
agrega a todo payload de pedido — este modal solo los lee del mismo
objeto `order` que recibe, igual que ya lee `items`/`total` (RF-4). El
identificador interno (`order.id`) nunca se renderiza en este modal;
sigue viajando en el payload (lo usa `ChargeOrderModal` para construir
la URL de `POST /api/pedidos/{id}/cobrar`), consistente con que RF-14
solo prohíbe mostrarlo como texto, no usarlo como identificador de
recurso.

### Panel "Opciones de pago" (gestión del catálogo — RF-2)

```
Opciones de pago
────────────────────────────────────
Efectivo                    (fija)
Nequi #1234                 [Eliminar]
Bancolombia Ahorros         [Eliminar] (bloqueado: ya tiene cobros)
────────────────────────────────────
Nombre nuevo: [____________]  [Agregar]
```

El botón "Eliminar" de una cuenta ya usada aparece deshabilitado (o,
si se toca, devuelve el error 409 de la sección 6) — nunca permite
confirmar una eliminación que el backend va a rechazar igual.

### Indicador y acción de corrección (en el pedido ya "cobrado")

Una vez cobrado, el pedido muestra en el panel de admin con qué opción
se pagó y un botón "Anular cobro" (RF-6), que pide un motivo (igual
patrón que "Anular pedido" ya existente en 003) y, si la mesa ya tiene
otro pedido activo, el backend lo rechaza (RF-6) y el modal muestra el
mensaje de error tal cual.

---

## 4. Garantizar "a lo sumo un cobro activo por pedido" bajo concurrencia

**Opción A — Verificar-y-crear dentro de una transacción con
`select_for_update()`.**

- A favor: patrón estándar de Django para evitar condiciones de
  carrera.
- En contra: `select_for_update()` no bloquea realmente filas en
  SQLite (Django lo ejecuta como no-op ahí) — dependería únicamente del
  lock de escritura global que SQLite ya aplica por archivo, sin nada
  que lo garantice de forma explícita si en el futuro se cambiara de
  motor de base de datos.

**Opción B — Restricción `UniqueConstraint` condicional en la propia
tabla `Payment`** (`unique_active_payment_per_order`, sección 2).

- A favor: la garantiza la base de datos misma, sin importar qué
  motor sea (SQLite hoy, cualquier otro mañana) ni cuántos procesos
  escriban a la vez; dos transacciones que intenten crear un `Payment`
  `ACTIVE` para el mismo pedido casi al mismo tiempo — la segunda
  siempre falla con un `IntegrityError`, que `services.py` traduce a
  "este pedido ya fue cobrado" (RF-1). No depende de recordar envolver
  cada lectura en un lock — es imposible de violar por accidente desde
  código nuevo.
- En contra: ninguno relevante aquí — ya se necesitaba esta tabla con
  o sin la restricción.

**Decisión: Opción B.** Resuelve a la vez el invariante de RF-7 (a lo
sumo un cobro activo) y la condición de carrera de RF-1 (rechazar el
segundo intento), con una sola línea de modelo, sin depender de un
comportamiento de SQLite que no aplicaría igual en otro motor.

---

## 5. Flujo

### `charge_order` (RF-1, RF-3, RF-5)

```
FUNCTION charge_order(order, admin, account):
    table = Table.objects.get(number=order.table_number)
    SI order.status != IN_PROGRESS O table.status != OCCUPIED:
        RECHAZAR 409("Este pedido no admite cobro en este momento.")

    total = sum(item.unit_price * item.quantity
                for item in order.items.all() if not item.is_voided)

    TRY (dentro de transaction.atomic()):
        payment = Payment.objects.create(
            order=order, account=account, amount=total, charged_by=admin,
        )
    EXCEPT IntegrityError:  # unique_active_payment_per_order (sección 4)
        RECHAZAR 409("Este pedido ya fue cobrado.")

    order.status = CHARGED
    order.save(update_fields=["status"])
    table.status = PAID
    table.save(update_fields=["status"])
    register_action(order, OrderAction.ActionType.CHARGED, admin)
    RETORNAR payment
```

### `void_charge` (RF-6)

```
FUNCTION void_charge(order, admin, reason):
    payment = Payment.objects.filter(order=order, status=ACTIVE).first()
    SI payment ES None:
        RECHAZAR 404("Este pedido no tiene ningún cobro activo.")

    mesa_reasignada = Order.objects.filter(
        table_number=order.table_number, status__in=(DRAFT, IN_PROGRESS)
    ).exclude(pk=order.pk).exists()
    SI mesa_reasignada:
        RECHAZAR 409("La mesa ya tiene un pedido nuevo; no se puede anular este cobro.")

    payment.status = VOIDED
    payment.voided_by = admin
    payment.voided_at = now()
    payment.void_reason = reason
    payment.save(update_fields=[...])

    order.status = IN_PROGRESS
    order.save(update_fields=["status"])

    table = Table.objects.get(number=order.table_number)
    SI table.status == PAID:
        table.status = OCCUPIED
        table.save(update_fields=["status"])

    notify_orders_changed()  # el pedido reaparece en "pedidos entrantes"
    RETORNAR order
```

### `create_account` / `delete_account` (RF-2)

```
FUNCTION create_account(name):
    SI name vacío O PaymentAccount.objects.filter(name=name).exists():
        RECHAZAR 400/409 según el caso
    RETORNAR PaymentAccount.objects.create(name=name)

FUNCTION delete_account(account):
    SI account.is_fixed:
        RECHAZAR 409("No se puede eliminar 'Efectivo'.")
    SI Payment.objects.filter(account=account).exists():
        RECHAZAR 409("Esta cuenta ya se usó en un cobro.")
    account.delete()
```

---

## 6. Contrato de API

Autenticación por cookie de sesión (heredada de 001). Todas las
respuestas de error usan `{"detail": "<mensaje>"}`. Todo endpoint de
esta sección exige rol admin (RF-8).

### Endpoint extendido de 003

| Endpoint | Método | RF | Request | Response 200 | Errores |
|-----------|--------|----|---------|-----------------|---------|
| `/api/pedidos/{id}/cobrar` | POST | RF-1, RF-3, RF-5 | `{"account_id": <int>}` | `{...pedido..., "active_payment": {...}}` | 400 falta `account_id`/cuenta no existe; 403 no es admin; 409 pedido no admite cobro o ya fue cobrado (carrera, sección 4) |

### Endpoints nuevos

| Endpoint | Método | RF | Request | Response | Errores |
|-----------|--------|----|---------|------------|---------|
| `/api/pedidos/{id}/cobro/anular` | POST | RF-6 | `{"reason": "<texto>"}` | `200 {...pedido..., "active_payment": null}` | 400 falta `reason`; 403 no es admin; 404 no hay cobro activo; 409 mesa ya reasignada (RF-6), o cobro ya anulado |
| `/api/cuentas-pago` | GET | RF-2 | — | `200 [{"id", "name", "is_fixed"}, ...]` | 403 no es admin |
| `/api/cuentas-pago` | POST | RF-2 | `{"name": "<texto>"}` | `201 {"id", "name", "is_fixed": false}` | 400 nombre vacío; 403 no es admin; 409 nombre duplicado |
| `/api/cuentas-pago/{id}` | DELETE | RF-2 | — | `204` | 403 no es admin; 404 no existe; 409 es "Efectivo" o ya se usó en un cobro |

`active_payment` (agregado a `GET /api/pedidos/{id}`, `/mios`,
`/entrantes`, y a las dos respuestas de arriba): `null` si el pedido no
está "cobrado"; si lo está, `{"account_name", "amount", "charged_by",
"charged_at"}` — el cobro `ACTIVE` vigente de ese pedido (RF-3, RF-7).
Este módulo no agrega ningún campo propio para identificar el pedido en
el consolidado: `numero_dia`/`enviado_en` (RF-4) ya vienen en el mismo
payload de pedido por `OrderSerializer` (003, plan sección 3, RF-14) —
`apps.payments` los lee, nunca los calcula ni los duplica.

---

## 7. Decisiones técnicas justificadas

1. **App Django separada (`apps/payments`)**, en vez de meter
   `PaymentAccount`/`Payment` dentro de `apps/orders`.
   Descartado: ampliar `apps/orders/models.py`. Mezclaría el dominio de
   pedidos con el de pagos, y obligaría a que cada test existente de
   003 conozca el catálogo de cuentas — mismo razonamiento que separó
   `apps/kitchen_printing` en 004.
2. **`UniqueConstraint` condicional en BD** para el invariante "a lo
   sumo un cobro activo por pedido" y la condición de carrera —
   justificada en la sección 4, descartando `select_for_update()`.
3. **Corregir un cobro es un nuevo registro (`status=VOIDED` en el
   mismo `Payment`), nunca un `UPDATE`/`DELETE`**, siguiendo el patrón
   de trazabilidad ya usado por `OrderAction` en 003.
   Descartado: una tabla `PaymentCorrection` aparte. Un único modelo
   con `status`/`voided_*` alcanza y evita una segunda tabla paralela
   sin necesidad.
4. **Monto cobrado como snapshot (`amount` `DecimalField`)**, calculado
   igual que `OrderSerializer.get_total` en el instante de cobrar, en
   vez de derivarlo del pedido cada vez que se consulta.
   Descartado: sin campo `amount`, solo con el total actual del pedido.
   Si luego se anula el cobro y el pedido vuelve a editarse (RF-6), el
   registro anulado dejaría de reflejar cuánto se había cobrado
   realmente en ese momento — exactamente lo que la spec pidió evitar.
5. **"Efectivo" como fila sembrada por una data migration
   (`is_fixed=True`)**, en vez de un valor especial fuera de la tabla
   (ej. `account_id=null` significa "efectivo").
   Descartado: tratar "efectivo" como un caso especial en código. Con
   una fila real, "Efectivo" es una opción más del mismo catálogo
   (mismo serializer, misma validación de que `account` exista), sin
   ramas especiales en `charge_order` ni en el frontend.
6. **Bloquear "anular cobro" verificando en el momento si la mesa ya
   tiene otro pedido activo** (`Order.objects.filter(table_number=...,
   status__in=(DRAFT, IN_PROGRESS))`), en vez de guardar un campo
   persistente tipo "mesa reasignada" en `Payment`.
   Descartado: marcar la mesa como "bloqueada para anular" al momento
   de reasignarla. Añadiría un campo y una sincronización extra para
   una comprobación que ya se puede hacer con una consulta directa en
   el momento exacto de la anulación — más simple y sin estado
   duplicado.
7. **`delete_account` valida en `services.py` si la cuenta ya se usó**
   (`Payment.objects.filter(account=account).exists()`), además de
   `on_delete=PROTECT` en el modelo.
   La validación en `services.py` da un mensaje de error claro (409,
   "ya se usó en un cobro"); `on_delete=PROTECT` queda como red de
   seguridad a nivel de base de datos si algún código futuro se salta
   el servicio.

---

## 8. Estrategia de tests

Cumpliendo la regla 6 de la constitución.

### Unitarios — `models.py`

- `PaymentAccount`: `name` único (crear dos con el mismo nombre falla);
  la fila "Efectivo" sembrada por la migración existe con
  `is_fixed=True`.
- `Payment`: dos `Payment` `ACTIVE` para el mismo `order` violan
  `unique_active_payment_per_order`; un `Payment` `VOIDED` para el
  mismo `order` sí se puede crear junto a uno `ACTIVE` nuevo.

### Unitarios — `services.py`

- `charge_order`: éxito con "Efectivo" y con una cuenta creada; guarda
  el monto exacto (ítems activos, sin los anulados — RF-4); rechaza si
  el pedido no está "en preparación" o la mesa no está "ocupada" (RF-1);
  rechaza el segundo intento si ya existe un `Payment` `ACTIVE` para
  ese pedido (simulando la carrera con dos llamadas seguidas, RF-1).
- `void_charge`: éxito cuando la mesa sigue "pagada" (vuelve a
  "ocupada") y cuando ya está "libre" sin reasignar; rechaza si no hay
  cobro activo (404); rechaza si ya está anulado; rechaza si la mesa ya
  tiene otro pedido activo (`DRAFT`/`IN_PROGRESS`, RF-6); exige
  `reason` no vacío; dispara `notify_orders_changed()` solo en el caso
  de éxito.
- `create_account`/`delete_account`: rechaza nombre vacío o duplicado;
  rechaza eliminar "Efectivo"; rechaza eliminar una cuenta con al menos
  un `Payment` (activo o anulado) asociado; éxito al eliminar una sin
  ningún uso.

### Integración (`DRF APIClient`)

- `POST /api/pedidos/{id}/cobrar`: 200 con `account_id` válido y
  `active_payment` en la respuesta; 400 sin `account_id`; 403 si quien
  llama no es admin (ni siquiera el mesero dueño); 409 en los mismos
  casos que el servicio.
- `POST /api/pedidos/{id}/cobro/anular`: 200 éxito (incluye `reason`);
  400 sin `reason`; 403 no-admin; 404 sin cobro activo; 409 mesa
  reasignada o cobro ya anulado.
- `GET`/`POST /api/cuentas-pago`, `DELETE /api/cuentas-pago/{id}`: cada
  código de respuesta de la tabla de la sección 6, con al menos un
  test.
- `GET /api/pedidos/{id}` (y `/mios`, `/entrantes`): `active_payment`
  aparece `null` antes de cobrar, y con los datos correctos después.
- RF-4, 003-RF-14: la respuesta de `POST /api/pedidos/{id}/cobrar`
  incluye `numero_dia`/`enviado_en` del pedido cobrado (ya puestos por
  003, no por este módulo); con un pedido sin número del día (enviado
  antes de este cambio), el cobro igual procede con esos campos en
  blanco.
- Ciclo completo: cobrar → anular → volver a cobrar con otra cuenta →
  el historial conserva ambos `Payment` (uno `VOIDED`, uno `ACTIVE`) sin
  que el primero se modifique.

### Canal en tiempo real

- Anular un cobro notifica `pedidos.actualizado` a un admin conectado a
  `/ws/pedidos/` (reutilizando el `WebsocketCommunicator` ya usado en
  los tests de 003); cobrar (como ya pasaba en 003) no lo hace.

---

## Cobertura de requisitos funcionales

| RF | Cubierto en |
|----|--------------|
| RF-1 | Sección 1 (`ChargeOrderView` → `apps.payments.services.charge_order`), Sección 4 (`UniqueConstraint`, condición de carrera), Sección 5 (pseudocódigo) |
| RF-2 | Sección 2 (`PaymentAccount`, migración de "Efectivo"), Sección 3 (panel de cuentas), Sección 5 (`create_account`/`delete_account`), Sección 6 (`/api/cuentas-pago`) |
| RF-3 | Sección 2 (`Payment`), Sección 5 (`charge_order`), Sección 6 (`active_payment`) |
| RF-4 | Sección 3 (modal de cobro, `numero_dia`/`enviado_en` heredados de 003-RF-14), Sección 5 (cálculo de `total`), Sección 6 (`active_payment`), Sección 8 |
| RF-5 | Sección 5 (`charge_order`: `order.status`, `table.status`) |
| RF-6 | Sección 2 (`Payment.status`/`voided_*`), Sección 3 (botón "Anular cobro"), Sección 5 (`void_charge`), Sección 6 (`/cobro/anular`), Decisión técnica 3 y 6 |
| RF-7 | Sección 2 (`unique_active_payment_per_order`), Sección 4 |
| RF-8 | Sección 1 (`permissions.py` reexporta `IsAdmin`), Sección 6 (todos los endpoints exigen admin) |
