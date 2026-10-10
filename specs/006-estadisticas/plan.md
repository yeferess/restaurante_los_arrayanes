# 006 · Estadísticas — Plan técnico

Este plan traduce a diseño técnico (el "cómo") la especificación aprobada
en `spec.md` (el "qué/por qué"). No contiene código, solo estructura,
contratos, pseudocódigo y decisiones justificadas.

## Cumplimiento de `docs/constitution.md`

- **Regla 1 (stack mínimo)**: solo Django + DRF, sobre las mismas tablas
  SQLite que ya existen (`orders.Order`, `orders.OrderItem`,
  `payments.Payment`, `payments.PaymentAccount`). Sin modelos nuevos, sin
  migraciones, sin Redis ni ninguna infraestructura de precálculo —
  consistente con el requisito no funcional de `spec.md` ("mientras el
  volumen de datos lo permita").
- **Regla 2 (offline-first en LAN)**: todos los endpoints de este módulo
  son REST sobre la LAN local; ninguno depende de un servicio externo.
- **Regla 3 (contrato de API)**: el frontend nunca calcula estas
  estadísticas ni consulta la base de datos directo — solo consume los
  endpoints de la sección 3.
- **Regla 4 (trazabilidad)**: no aplica — este módulo no introduce
  ninguna acción de escritura ni acción sensible nueva.
- **Regla 5 (permisos por rol)**: RF-8 se implementa reutilizando
  `IsAdmin` (ya existente, sección 1). Por decisión ya tomada en
  `spec.md` ("Dudas abiertas"), **no se amplía** el texto de la regla 5
  de la constitución — a diferencia de 005-cobro, que sí la amplió para
  sus acciones de escritura nuevas.
- **Regla 6 (tests obligatorios)**: sección 6 cubre cada función de
  agregación y cada endpoint.
- **Regla 7 (idioma)**: nombres de clases/campos/variables en inglés en
  el código real (`day_summary`, `range_summary`, `day_movement`, etc.);
  este documento permanece en español.

---

## 1. Estructura de módulos/archivos

### Backend (`/backend`)

```
backend/
  apps/
    stats/                        # app dedicada (RF-1..RF-10), de solo
                                   # lectura — sin models.py, sin
                                   # migraciones (regla 1)
      services.py                  # day_summary(), range_summary(),
                                    # day_movement() — lógica de
                                    # agregación pura, sin HTTP
      permissions.py                # reexporta IsAdmin de apps.orders
      views.py                      # 3 endpoints (sección 3)
      urls.py                       # incluido en config/urls.py bajo
                                     # /api/
      apps.py
      tests/
        test_setup.py
        test_services_day_summary.py
        test_services_range_summary.py
        test_services_day_movement.py
        test_services_stability.py    # RF-10
        test_views_stats.py
        test_permissions.py
```

`apps.stats` importa de `apps.orders` (`Order`, `OrderItem`) y de
`apps.payments` (`Payment`, `PaymentAccount`) — misma dirección de
dependencia que ya establecieron 004 (`kitchen_printing`) y 005
(`payments`) al importar de `apps.orders`. Ninguno de esos módulos
importa nada de `apps.stats` (regla 3: es un consumidor de solo
lectura, nunca una dependencia de otro módulo).

### Frontend (`/frontend`, Next.js App Router)

```
frontend/
  app/
    admin/(panel)/
      estadisticas/page.tsx         # RF-1 a RF-6 — panel de
                                     # estadísticas del admin
  lib/api/
    stats.ts                        # getDaySummary(date?),
                                     # getRangeSummary(from, to),
                                     # getDayMovement(date)
  components/
    DaySummaryPanel.tsx              # RF-1, RF-2, RF-3, RF-4 (vista
                                      # "hoy" o un día específico)
    DateRangeFilter.tsx               # RF-5 (selector desde/hasta)
    DayMovementView.tsx                # RF-6 (listas de pedidos y
                                        # cobros de un día)
```

---

## 2. Modelo de datos

Ninguno. Este módulo no define ninguna tabla nueva — RF-9 exige que sea
estrictamente de lectura, y la sección 1 ya establece que no hay
`models.py`. Toda la información se deriva en cada solicitud a partir
de `Order`, `OrderItem`, `Payment` y `PaymentAccount` (003/005), usando
siempre el identificador interno del pedido como llave de cruce (RF-7),
nunca el número del día.

---

## 3. Contrato de la API

Todos los endpoints viven bajo `/api/estadisticas/`. Autenticación por
cookie de sesión (heredada de 001). Todo endpoint exige rol admin
(RF-8). Todas las respuestas de error usan `{"detail": "<mensaje>"}`.

| # | Endpoint | Método | RF | Query params | Response 200 | Errores |
|---|-----------|--------|----|--------------|-----------------|---------|
| 1 | `/api/estadisticas/resumen` | GET | RF-1, RF-2, RF-3, RF-4 | `date` (opcional, default hoy) | `{"date", "money_total", "orders_charged_count", "money_by_account": [...], "orders_by_waiter": [...], "top_products": [...]}` | 400 `date` inválida; 403 mesero |
| 2 | `/api/estadisticas/rango` | GET | RF-2, RF-3, RF-4, RF-5 | `from`, `to` (ambos obligatorios) | `{"from", "to", "money_total", "orders_sent_count", "money_by_account": [...], "orders_by_waiter": [...], "top_products": [...]}` | 400 falta `from`/`to`, formato inválido, o `from` > `to`; 403 mesero |
| 3 | `/api/estadisticas/movimiento` | GET | RF-6 | `date` (opcional, default hoy) | `{"date", "orders": [{"daily_number", "waiter", "status", "total"}], "payments": [{"account_name", "amount", "charged_by", "charged_at", "status"}]}` | 400 `date` inválida; 403 mesero |

Notas de contrato:
- `money_by_account`: `[{"account_name", "total"}]`, ordenado de mayor a
  menor; una cuenta sin cobros en el período no aparece (RF-2).
- `orders_by_waiter`: `[{"waiter_username", "orders_sent"}]`, ordenado de mayor a
  menor; un mesero sin pedidos en el período no aparece (RF-3).
- `top_products`: `[{"product_name", "quantity"}]`, máximo 10, ordenado
  de mayor a menor cantidad (RF-4).
- `date`/`from`/`to` usan formato `YYYY-MM-DD`, interpretado siempre en
  hora local del restaurante (`America/Bogota`), nunca UTC.
- Una fecha `to` futura es válida (RF-5); los endpoints 1 y 3 no
  rechazan una `date` futura tampoco — simplemente no habrá datos.
- El campo `id` interno del pedido **nunca** aparece en estas
  respuestas — ni siquiera como identificador de recurso, porque
  ningún endpoint de este módulo opera sobre un pedido individual
  (RF-7); `daily_number` ya identifica cada fila de `orders` en el
  endpoint 3.

---

## 4. Agregaciones (RF-1 a RF-6)

### `_date_range(start, end)` — base común

Las tres funciones de `services.py` comparten un único criterio de
corte de fecha: `start`/`end` son objetos `date` (ya en hora local,
nunca UTC), y toda comparación contra `sent_at`/`charged_at` usa el
lookup `__date` de Django, que interpreta `DateTimeField` en la zona
horaria activa (`TIME_ZONE = "America/Bogota"`, ya configurada desde
003-RF-14) — mismo mecanismo que ya usa `timezone.localdate()` en
`apps.orders.services._assign_daily_number`.

### RF-1/RF-2/RF-5 — dinero (criterio: `charged_at`, con estabilidad RF-10)

```
FUNCTION _qualifying_payments(start, end):
    RETORNAR Payment.objects
        .annotate(charged_date=TruncDate("charged_at"),
                  voided_date=TruncDate("voided_at"))
        .filter(charged_date__range=(start, end))
        .filter(
            Q(status=ACTIVE) | Q(voided_date__gt=F("charged_date"))
        )

FUNCTION money_total(start, end):
    RETORNAR _qualifying_payments(start, end).aggregate(Sum("amount"))

FUNCTION orders_charged_count(start, end):
    RETORNAR _qualifying_payments(start, end)
        .values("order_id").distinct().count()

FUNCTION money_by_account(start, end):
    RETORNAR _qualifying_payments(start, end)
        .values(account_name=F("account__name"))
        .annotate(total=Sum("amount"))
        .order_by("-total")
```

`_qualifying_payments` es, en una sola consulta, la implementación
completa de RF-10 (sección 5, decisión 1): un `Payment` cuenta para el
total de **su propio** día de cobro si sigue `ACTIVE`, o si se anuló en
una fecha **posterior** a la de su cobro — comparar `voided_date` contra
el propio `charged_date` del mismo registro (no contra "hoy" ni contra
la fecha de la consulta) es lo que hace que el total de un día ya
cerrado nunca cambie, sin necesitar ningún snapshot ni tabla aparte.

### RF-3/RF-5 — pedidos por mesero (criterio: `sent_at`)

```
FUNCTION orders_sent_count(start, end):
    RETORNAR Order.objects.filter(sent_at__date__range=(start, end)).count()

FUNCTION orders_by_waiter(start, end):
    RETORNAR Order.objects.filter(sent_at__date__range=(start, end))
        .values(waiter_username=F("waiter__username"))  # "waiter" ya es
        # un campo del modelo Order, no se puede reusar como alias
        .annotate(orders_sent=Count("id"))
        .order_by("-orders_sent")
```

Ningún filtro adicional de `status`: un pedido enviado cuenta sin
importar si terminó cobrado, en preparación, o anulado (spec.md, RF-3).

### RF-4 — productos más vendidos (criterio: `sent_at`, vía el pedido)

```
FUNCTION top_products(start, end):
    RETORNAR OrderItem.objects
        .filter(order__sent_at__date__range=(start, end),
                is_voided=False,
                catalog_product__isnull=False)
        .exclude(order__status=VOIDED)
        .values(product_name=F("catalog_product__name"))
        .annotate(quantity=Sum("quantity"))
        .order_by("-quantity")[:10]
```

`catalog_product__isnull=False` cubre, en una sola condición, dos
reglas de `spec.md`: excluye los ítems fuera de carta (nunca tienen
`catalog_product`), y excluye automáticamente los productos ya
eliminados del catálogo (`on_delete=SET_NULL` los deja en `NULL` para
siempre) — ninguna de las dos exclusiones necesita una condición
aparte.

### RF-6 — movimiento de un día

```
FUNCTION day_movement(date):
    pedidos = Order.objects.filter(sent_at__date=date).select_related("waiter")
    cobros = Payment.objects.annotate(charged_date=TruncDate("charged_at"))
        .filter(charged_date=date).select_related("account", "charged_by")
    RETORNAR {
        "orders": [serializar cada pedido: daily_number, waiter.username,
                   status, total ACTUAL (mismo cálculo que
                   OrderSerializer.get_total, sección 005)],
        "payments": [serializar cada cobro: account.name, amount,
                     charged_by.username, charged_at, status],
    }
```

El total de cada pedido se calcula leyendo sus ítems **actuales**
(spec.md, RF-6) — no hay ningún snapshot que reconstruir, es la misma
lectura que ya hace `OrderSerializer.get_total` en `apps.orders`.

---

## 5. Decisiones técnicas justificadas

1. **Estabilidad de días cerrados (RF-10) resuelta con una comparación
   de fechas sobre el propio registro (`voided_date__gt=charged_date`),
   no con una tabla de cierre/snapshot por día.**
   Descartado: guardar un "cierre de caja" diario que congele los
   totales explícitamente. Compararle a cada `Payment` su propia fecha
   de anulación contra su propia fecha de cobro ya produce el mismo
   resultado (el total de un día pasado nunca cambia retroactivamente,
   salvo por una anulación del mismo día) sin necesitar una tabla ni
   un proceso de cierre — consistente con la regla 1 (sin
   infraestructura adicional) y con la decisión ya tomada en `spec.md`
   de no comprometerse a una fecha de corte de rendimiento.

2. **Sin app ni modelo compartido entre las tres agregaciones** — todas
   viven como funciones de `apps/stats/services.py`, sin una capa de
   caché ni de materialización intermedia.
   Descartado: una vista materializada o una tabla de resumen
   recalculada por un job periódico. El RNF de `spec.md` ya documenta
   que esa decisión queda abierta para el futuro si el volumen de datos
   lo exige — hoy, con consultas directas sobre índices ya existentes
   (`charged_at`, `sent_at`), no hace falta.

3. **`catalog_product__isnull=False` como único filtro para "producto
   de catálogo"** (RF-4), en vez de un campo nuevo que distinga
   "viene de catálogo" de forma permanente.
   Descartado: agregar un campo a `OrderItem` (ej.
   `is_catalog_item`, inmutable) que sobreviviera a la eliminación del
   producto. `spec.md` ya resolvió esta ambigüedad explícitamente:
   un producto eliminado deja de contar en el ranking desde su
   eliminación en adelante — exactamente el comportamiento que produce
   `on_delete=SET_NULL` sin tocar el modelo de 003.

4. **Dos endpoints distintos para "día" y "rango"** (`/resumen` y
   `/rango`), en vez de uno solo con parámetros opcionales mutuamente
   excluyentes.
   Descartado: una sola ruta `/resumen?date=...&from=...&to=...` que
   decida su comportamiento según qué parámetros lleguen. Dos rutas con
   contratos propios son más simples de validar (400 claro por ruta) y
   reflejan directamente la separación que ya hace `spec.md` entre RF-1
   y RF-5.

---

## 6. Estrategia de tests

Cumpliendo la regla 6 de la constitución.

### Unitarios (`Django TestCase`, sin HTTP — prueban `services.py`)

- RF-1: `money_total`/`orders_charged_count` de un día con varios
  cobros activos y uno anulado (el anulado no suma); un pedido cobrado,
  anulado y vuelto a cobrar el mismo día cuenta una sola vez.
- RF-2: `money_by_account` desglosa correctamente entre dos o más
  cuentas; una cuenta sin cobros ese día no aparece.
- RF-3: `orders_by_waiter` cuenta todo pedido enviado sin importar su
  estado final (en preparación, cobrado, anulado); un pedido en
  borrador nunca cuenta; un mesero sin pedidos no aparece.
- RF-4: `top_products` excluye ítems fuera de carta, ítems anulados, e
  ítems de un pedido anulado por completo (aunque el ítem en sí no esté
  marcado `is_voided`); una adición agregada días después se atribuye
  al día de envío original del pedido; un producto eliminado del
  catálogo después de vendido deja de aparecer; se recorta a 10.
- RF-5: `range_summary` combina correctamente varios días; `from` >
  `to` se rechaza a nivel de vista (sección de integración); una fecha
  `to` futura no rompe el cálculo, solo no aporta datos.
- RF-6: `day_movement` incluye pedidos/cobros anulados; un cobro
  anulado un día distinto al de su registro aparece solo en el
  movimiento de su `charged_at` original; un día sin movimiento
  devuelve listas vacías.
- **RF-10** (dedicado, `test_services_stability.py`): un cobro anulado
  el día siguiente a su registro no cambia el total ya calculado para
  el día del cobro original; un cobro anulado el **mismo** día sí se
  excluye; consultar el mismo día antes y después de una anulación
  tardía produce el mismo resultado (estable).

### Integración (`DRF APIClient`, HTTP real)

- Los 3 endpoints de la sección 3: 200 con cada parámetro válido, 400
  con fecha inválida o `from` > `to`, 403 para un mesero, 401 sin
  sesión.
- Un mesero autenticado recibe 403 en los tres endpoints (RF-8).
- Flujo completo: pedido enviado → cobrado → aparece en `/resumen`,
  `/rango` y `/movimiento` del día correspondiente, con su número del
  día (nunca su id interno) en la respuesta de `/movimiento`.

---

## Cobertura de requisitos funcionales

| RF | Cubierto en |
|----|--------------|
| RF-1 | Sección 3 (endpoint 1), Sección 4 (`money_total`, `orders_charged_count`), Sección 6 |
| RF-2 | Sección 3 (endpoints 1-2), Sección 4 (`money_by_account`), Sección 6 |
| RF-3 | Sección 3 (endpoints 1-2), Sección 4 (`orders_by_waiter`), Sección 6 |
| RF-4 | Sección 3 (endpoints 1-2), Sección 4 (`top_products`), Decisión técnica 3, Sección 6 |
| RF-5 | Sección 3 (endpoint 2), Sección 4, Decisión técnica 4, Sección 6 |
| RF-6 | Sección 3 (endpoint 3), Sección 4 (`day_movement`), Sección 6 |
| RF-7 | Sección 2 (llave interna), Sección 3 (nota de contrato: nunca se expone el id interno) |
| RF-8 | Sección 1 (`permissions.py` reexporta `IsAdmin`), Sección 3 (todos los endpoints), Sección 6 |
| RF-9 | Sección 2 (sin modelo nuevo, sin escritura en ninguna función de `services.py`) |
| RF-10 | Sección 4 (`_qualifying_payments`), Decisión técnica 1, Sección 6 |
