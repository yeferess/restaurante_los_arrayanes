# 004 · Impresión en cocina — Plan técnico

Este plan traduce a diseño técnico (el "cómo") la especificación
aprobada en `spec.md` (el "qué/por qué"). No contiene código, solo
estructura, contratos, pseudocódigo y decisiones justificadas.

## Cumplimiento de `docs/constitution.md`

- **Regla 1 (stack mínimo)**: se suma únicamente una dependencia Python
  para hablar con la cola de impresión de Windows (`pywin32`); no se
  agrega Redis, Celery, Postgres ni ningún servicio externo.
- **Regla 2 (offline-first en LAN)**: la impresora es un periférico USB
  del mismo equipo donde corre el backend; ningún paso de este módulo
  depende de la red ni de internet.
- **Regla 3 (contrato de API)**: el frontend nunca habla con la
  impresora ni con `pywin32` — solo consume los campos/endpoints de la
  sección 6.
- **Regla 4 (trazabilidad)**: no aplica a este módulo de forma directa
  (reintentar impresión no es una anulación, un cambio de mesa, un
  cobro ni una acción sensible de cuentas); `PrintJob` igual queda con
  su propio rastro de quién es el pedido y cuántos intentos tuvo, por
  diseño, no porque la regla 4 lo exija.
- **Regla 5 (permisos por rol)**: **no se amplía** — tal como resolvió
  `spec.md`, "reintentar impresión" queda implícito dentro de lo que el
  mesero ya puede hacer sobre sus propios pedidos; el permiso se aplica
  igual (`IsOrderOwner`, reutilizado de 003), solo que sin una entrada
  nueva en el texto de la regla 5.
- **Regla 6 (tests obligatorios)**: sección 8 cubre unitarios,
  integración con impresora simulada, y una checklist manual para lo
  que ningún test automatizado puede verificar (el hardware real).
- **Regla 7 (idioma)**: nombres de clases/campos/variables en inglés en
  el código real (`PrintJob`, `PrinterAdapter`, `ticket_type`, etc.);
  este documento permanece en español.

---

## 1. Estructura de módulos/archivos

### Backend (`/backend`)

```
backend/
  apps/
    kitchen_printing/              # app dedicada (RF-1..RF-11), separada
                                    # de apps.orders a propósito
      models.py                    # PrintJob (sección 2)
      adapters.py                  # PrinterAdapter (interfaz) +
                                    # EscposUsbPrinterAdapter (real) +
                                    # FakePrinterAdapter (tests)
      rendering.py                 # arma el texto exacto de cada ticket
                                    # a partir de Order/OrderItem/OrderAction
                                    # (sección 3)
      services.py                  # register_event_and_print(...),
                                    # retry_print(...) — consolidación
                                    # (RF-8), orquesta rendering + adapter
                                    # + PrintJob (sección 5)
      permissions.py               # reexporta IsOrderOwner de apps.orders
      views.py                     # POST /api/pedidos/{id}/reimprimir
      urls.py                      # incluido en config/urls.py bajo /api/
      apps.py
      tests/
        test_rendering.py
        test_services.py
        test_adapters_fake.py
        test_views_retry.py
        test_integration_fake_printer.py
        test_realtime_propagation.py
```

`apps/orders/services.py` (ya existente, de 003) se modifica de forma
mínima — tres funciones llaman al nuevo módulo justo después de guardar
el cambio de negocio, nunca antes:

```python
# send_order(order): después de order.save(update_fields=["status"])
kitchen_printing.services.register_event_and_print(
    order, event_type=PrintJob.TicketType.NEW_ORDER
)

# add_item(...): solo en la rama line_type == ADDITION
kitchen_printing.services.register_event_and_print(
    order, event_type=PrintJob.TicketType.ADDITION
)

# void_item(...): solo si NO se auto-anuló el pedido completo
kitchen_printing.services.register_event_and_print(
    order, event_type=PrintJob.TicketType.VOID
)
```

`apps.orders` no importa nada de la implementación interna de
`kitchen_printing` más allá de esa única función de `services.py` — la
separación que pide el prompt original (sección 1, punto 1).

### Frontend (`/frontend`, Next.js App Router)

```
frontend/
  lib/api/
    orders.ts                   # + retryPrint(orderId): Promise<Order>
                                 #   POST /api/pedidos/{id}/reimprimir
                                 # + type Order gana has_pending_print
                                 #   y print_warning?: string
  components/
    MyOrdersList.tsx             # + badge "No impreso en cocina" y botón
                                  #   "Reintentar impresión" cuando
                                  #   has_pending_print && status no es
                                  #   CHARGED/VOIDED (decisión técnica 7)
    IncomingOrdersPanel.tsx       # + mismo badge, solo lectura (sin botón)
```

No se agregan páginas nuevas: el badge/botón vive dentro de los
componentes que 003 ya construyó para "Mis pedidos" y "Pedidos
entrantes".

---

## 2. Modelo de datos

Según RF-8/RF-10 de la spec, el contenido de un ticket **nunca** se
guarda congelado — se regenera con el estado actual en cada intento. Por
eso la única tabla nueva que hace falta es un registro de **qué ticket
está pendiente y cuántas veces se intentó**, no un snapshot de su
contenido.

### Tabla `PrintJob` (ticket de cocina — RF-8, RF-9, RF-10)

| Campo         | Tipo                                                        | Restricciones                                                        | RF    |
|----------------|------------------------------------------------------------|-----------------------------------------------------------------------|-------|
| `id`           | `AutoField`                                                 | PK                                                                     | —     |
| `order`        | `ForeignKey(Order, on_delete=PROTECT)`                      | mismo criterio que `OrderAction` en 003                                | RF-8  |
| `ticket_type`  | `CharField` choices `NEW_ORDER` / `ADDITION` / `VOID`        | fijo desde la creación, aunque se le consolide un evento de otro tipo  | RF-8  |
| `status`       | `CharField` choices `PENDING` / `PRINTED`                   | default `PENDING`                                                      | RF-9, RF-10 |
| `attempts`     | `PositiveIntegerField`                                      | default `1`; se incrementa en cada intento (original o reintento)      | RF-9  |
| `created_at`   | `DateTimeField(auto_now_add=True)`                           | momento del primer evento que originó este ticket                     | —     |
| `printed_at`   | `DateTimeField(null=True, blank=True)`                       | se fija la primera vez que un intento tiene éxito; de ahí en más el ticket queda cerrado | RF-8, RF-10 |

**No se guarda** ninguna lista de ítems ni texto de ticket en esta
tabla — ver sección 5 para cómo se deriva el contenido en cada intento.
**No se guarda** un campo `waiter` propio: el mesero relevante siempre
es `order.waiter` (dueño fijo e inmutable, 003 RF-7), así que
`print_job.order.waiter` ya alcanza.

Invariante que mantiene `services.py` (sección 5): **como máximo un
`PrintJob` con `status=PENDING` por pedido a la vez** — es la regla de
consolidación de RF-8.

**Ejemplo de registro** (segundo intento, sigue fallando):

```json
{
  "id": 7,
  "order_id": 41,
  "ticket_type": "NEW_ORDER",
  "status": "PENDING",
  "attempts": 2,
  "created_at": "2026-03-10T20:15:00Z",
  "printed_at": null
}
```

---

## 3. Diseño de los tickets

Ancho configurable por settings:

```python
# config/settings.py
KITCHEN_PRINTER_COLUMNS = 40  # Epson TM-U220, Font A estándar
```

**Regla de ajuste de línea**: toda línea que exceda
`KITCHEN_PRINTER_COLUMNS` se parte con `textwrap.wrap`, con sangría
colgante de 4 espacios (el ancho de `"99x "`) para que el nombre del
ítem quede alineado en las líneas siguientes, nunca cortando una
palabra a mitad.

**Encabezado de identificación** (RF-2, 003-RF-14): cada ticket muestra
el número del día del pedido con el formato "N° " + entero simple (sin
ceros a la izquierda), la fecha y hora de envío, y la hora del intento
de impresión — esta última es un dato distinto, ya existente desde
antes de RF-14, y las dos conviven en el mismo ticket sin confundirse
(cada una con su propia etiqueta). **Nunca** el identificador interno
del pedido. Las dos marcas de tiempo se imprimen con el mismo tamaño de
letra que el resto del ticket — texto plano de un solo estilo, sin la
jerarquía visual que 003-RF-14 exige en pantalla (spec, excepción ya
resuelta). Si el pedido no tiene número del día (enviado antes de este
cambio), el campo se imprime en blanco en su lugar (003-RF-14, caso
transitorio).

**Bloque de notas** (RF-6): una línea por nota, con el marcador
`*** NOTA (ítem): texto ***` en mayúsculas, envuelta con la misma regla
de ajuste si no cabe en una línea.

**Sin color rojo** (RF-7): todo el ticket se manda como texto ESC/POS
plano en el color por defecto de la cinta instalada — este módulo nunca
emite el comando ESC/POS de cambio de color.

### Maqueta — "PEDIDO NUEVO" (RF-2, RF-3, RF-6, RF-7)

```
========================================
          PEDIDO NUEVO - MESA 5
========================================
N° 7                  Enviado 10/03 20:15
Mesero: cgarcia       Impreso 10/03 20:16
----------------------------------------
*** NOTA (LIMONADA NATURAL):
    SIN AZUCAR ***
----------------------------------------
2x Limonada natural
1x Sancocho de gallina
1x Postre de la casa (fuera de carta)
========================================
```

### Maqueta — "ADICIÓN" (RF-2, RF-4, RF-6, RF-7)

```
========================================
            ADICION - MESA 5
========================================
N° 7                  Enviado 10/03 20:15
Mesero: cgarcia       Impreso 10/03 20:32
----------------------------------------
1x Jugo de naranja
1x Arroz con pollo gigante especial de
    la casa para compartir
========================================
```
(la segunda línea de ítem muestra la sangría colgante por un nombre que
excede las 40 columnas.)

### Maqueta — "ANULACIÓN" (RF-2, RF-5, RF-6, RF-7)

```
========================================
           ANULACION - MESA 5
========================================
N° 7                  Enviado 10/03 20:15
Mesero: cgarcia       Impreso 10/03 20:40
----------------------------------------
1x Sancocho de gallina
    Motivo: cliente cambio de pedido
========================================
```

Si un ticket pendiente consolida más de un evento (RF-8), el encabezado
no cambia — por ejemplo un "ADICIÓN" que luego absorbe una anulación
antes de imprimirse muestra ambas secciones (ítems agregados e ítems
anulados) bajo el mismo encabezado "ADICIÓN – Mesa N", sin inventar un
cuarto tipo de encabezado "mixto" (decisión técnica 2).

---

## 4. Conexión con la impresora en Windows por USB

**Opción A — Acceso directo al dispositivo USB** (ej. `python-escpos`
con backend `usb`, vía `pyusb`/`libusb`).

- A favor: no depende de que la impresora esté bien instalada como
  impresora de Windows; es el patrón más común en los ejemplos de
  `python-escpos`.
- En contra: en Windows exige instalar un driver genérico (libusb, vía
  la herramienta Zadig) que **reemplaza** el driver oficial de Epson —
  si el restaurante también usa esa impresora desde Windows de forma
  directa (ej. imprimir una página de prueba desde el panel de
  impresoras), ese uso se rompe. Es un paso manual frágil de mantener
  en un portátil normal, y el VID/PID queda hardcodeado.

**Opción B — Enviar los bytes ESC/POS como trabajo RAW a la cola de
impresión de Windows, usando el driver oficial de Epson ya instalado**
(`pywin32`, módulo `win32print`).

- A favor: reutiliza el driver oficial que el restaurante ya tendría
  instalado para usar la impresora normalmente; Windows administra la
  detección de "impresora apagada/desconectada" vía la API del spooler
  (`win32print.OpenPrinter` + `GetPrinter`), sin pelear con drivers
  alternativos; no interfiere con ningún otro uso de la misma impresora
  desde el mismo equipo.
- En contra: el reporte de estado vía spooler es más limitado que leer
  el status byte ESC/POS directo (no alcanza para distinguir "sin
  papel" de "sin cinta" con certeza) — pero la spec ya resolvió que
  **no hace falta** esa distinción fina (RF-9: solo "impresora no
  detectada" vs. "error al imprimir").

**Decisión: Opción B.** El equipo es un portátil Windows normal de un
restaurante, no un servidor dedicado a esto — pedirle al dueño que
instale un driver alternativo (Zadig) es fricción operativa innecesaria
y arriesga romper otros usos de la misma impresora. La API de spooler
de Windows ya alcanza para las dos categorías de fallo que pide RF-9, y
es exactamente el patrón que "simplemente funciona" en un Windows
normal con el driver del fabricante ya instalado.

---

## 5. Flujo de impresión

El pedido/ítem **siempre se guarda primero** — en `apps/orders/services.py`
ya es así desde 003 (el `.save()`/`.create()` ocurre antes de cualquier
llamada a `kitchen_printing`); un fallo de impresión nunca puede revertir
ni perder esa escritura, porque ocurre después y en una transacción ya
confirmada.

La impresión es **síncrona**, dentro de la misma solicitud HTTP que
originó el evento (RF-9: el mesero necesita el resultado real, no una
promesa a futuro). Como la impresora es un recurso físico único y el
requisito no funcional exige que los tickets salgan en orden sin
solaparse, `kitchen_printing.services` usa un `threading.Lock()` a nivel
de módulo (un solo proceso Daphne/ASGI, sin multi-worker — consistente
con la regla 1): cualquier solicitud que llegue mientras el lock está
tomado espera su turno antes de intentar imprimir, y antes de responder.

### Pseudocódigo

```
LOCK = threading.Lock()

FUNCTION register_event_and_print(order, event_type):
    CON LOCK:
        job = PrintJob.objects.filter(order=order, status=PENDING).first()
        SI job ES None:
            job = PrintJob.objects.create(order=order, ticket_type=event_type)
        # si ya había uno pendiente, se reutiliza (RF-8): el tipo original
        # del ticket NO cambia aunque event_type sea distinto

        texto = rendering.build_ticket_text(job)   # siempre con el estado actual
        job.attempts += 1
        TRY:
            adapter.print_ticket(texto)
            job.status = PRINTED
            job.printed_at = now()
            job.save()
            RETORNAR print_warning=None
        EXCEPT PrinterNotDetectedError:
            job.save()
            RETORNAR print_warning="No se pudo imprimir: impresora no detectada."
        EXCEPT PrinterFailureError:
            job.save()
            RETORNAR print_warning="No se pudo imprimir el ticket en cocina."

FUNCTION retry_print(order, waiter):
    SI order.waiter != waiter:
        RECHAZAR 403()
    SI order.status EN (CHARGED, VOIDED):
        RECHAZAR 409("Este pedido ya no admite reimpresión.")
    job = PrintJob.objects.filter(order=order, status=PENDING).first()
    SI job ES None:
        RECHAZAR 404("No hay ningún ticket pendiente para este pedido.")
    # reintenta con la misma lógica de arriba (CON LOCK, regenerar texto, …)
    resultado = _attempt(job)
    SI resultado.exito:
        notificar_pedidos_actualizados()   # reutiliza el canal de 003
    RETORNAR 200(order_payload, print_warning=resultado.aviso)
```

`rendering.build_ticket_text(job)` calcula, en cada llamada:

```
referencia = PrintJob.objects.filter(
    order=job.order, status=PRINTED
).order_by("-printed_at").first()
desde = referencia.printed_at if referencia else job.order.created_at

items_nuevos = job.order.items.filter(is_voided=False, created_at__gt=desde)
anulaciones = OrderAction.objects.filter(
    order=job.order, action_type=ITEM_VOIDED, timestamp__gt=desde
)
```
— nunca lee un texto guardado; siempre arma el ticket con lo que haya
cambiado desde el último éxito, incluyendo el caso "primer ticket del
pedido" (`desde = order.created_at`, trae todos los ítems activos,
cubriendo RF-3).

El mesero se entera del resultado por dos vías, ambas ya contempladas
en el contrato (sección 6): el campo `print_warning` en la respuesta
inmediata de esa misma acción (RF-9), y el campo persistente
`has_pending_print` que queda en `true` en cualquier lectura posterior
del pedido mientras el `PrintJob` siga `PENDING` (RF-10).

---

## 6. Contrato de la API

Autenticación por cookie de sesión (heredada de 001). Todas las
respuestas de error usan `{"detail": "<mensaje>"}`.

### Endpoint nuevo

| Endpoint | Método | RF | Auth | Request | Response 200 | Errores |
|-----------|--------|----|------|---------|-----------------|---------|
| `/api/pedidos/{id}/reimprimir` | POST | RF-9, RF-10, RF-11 | dueño | — | `{...pedido..., "print_warning": null \| "<mensaje>"}` | 403 no es el dueño; 404 pedido no existe o no hay ticket pendiente; 409 pedido ya cobrado o anulado |

### Extensión de los endpoints existentes de 003

Los tres endpoints de 003 que disparan impresión agregan el mismo campo
opcional a su respuesta de éxito — **su código HTTP no cambia** por un
fallo de impresión (decisión técnica 5):

| Endpoint (003) | RF que dispara impresión | Campo agregado |
|-----------------|-----------------------------|-------------------|
| `POST /api/pedidos/{id}/enviar` | RF-1 (ticket "PEDIDO NUEVO") | `print_warning: null \| "<mensaje>"` |
| `POST /api/pedidos/{id}/items` (con el pedido ya "en preparación") | RF-1 (ticket "ADICIÓN") | `print_warning: null \| "<mensaje>"` |
| `POST /api/pedidos/{id}/items/{item_id}/anular` (sin auto-anular el pedido) | RF-1 (ticket "ANULACIÓN") | `print_warning: null \| "<mensaje>"` |

Y los endpoints de lectura de 003 agregan el campo persistente del
indicador:

| Endpoint (003) | Campo agregado |
|-----------------|-------------------|
| `GET /api/pedidos/mios` | `has_pending_print: boolean` por pedido |
| `GET /api/pedidos/entrantes` | `has_pending_print: boolean` por pedido |
| `GET /api/pedidos/{id}` | `has_pending_print: boolean` |

Los dos mensajes posibles de `print_warning` (RF-9): `"No se pudo
imprimir: impresora no detectada."` / `"No se pudo imprimir el ticket
en cocina."` (error genérico al imprimir). Ningún otro texto distinto.

---

## 7. Decisiones técnicas justificadas

1. **App Django separada (`kitchen_printing`) con un adaptador
   (`PrinterAdapter`)**, en vez de meter la lógica de impresión directo
   en `apps/orders/services.py`.
   Descartado: acoplar la impresión a `apps.orders`. Mezclaría negocio
   de pedidos con hardware, y haría imposible testear `send_order`/
   `add_item`/`void_item` sin depender de una impresora simulada en
   cada test de 003 ya existente — rompería tests que hoy no saben nada
   de impresión.

2. **Encabezado fijo del tipo original cuando un ticket pendiente
   consolida eventos de otro tipo** (ej. "ADICIÓN" que absorbe una
   anulación antes de imprimirse muestra ambas secciones bajo el mismo
   encabezado).
   Descartado: un cuarto tipo de encabezado "mixto", o cambiar el
   encabezado al evento más reciente. La spec ya resolvió que el
   encabezado "es el mismo" (no cambia); inventar un tipo nuevo
   complicaría `PrintJob.ticket_type` sin necesidad.

3. **Contenido derivado en cada intento** (consultando
   `OrderItem.created_at`/`OrderAction.timestamp` posteriores al
   `printed_at` del último ticket exitoso), en vez de guardar una lista
   congelada de ítems por `PrintJob`.
   Descartado: una tabla `PrintJobItem` tipo snapshot. La spec (RF-8,
   RF-10) exige expresamente regenerar con el estado actual, nunca un
   texto congelado — una snapshot persistida sería trabajo extra que
   además contradice esa regla.

4. **Cola de impresión de Windows (`win32print`, trabajo RAW con el
   driver oficial de Epson)** en vez de acceso directo al USB vía
   libusb — justificada en la sección 4.

5. **La impresión nunca cambia el código HTTP de la acción que la
   originó** (sigue siendo 200/201 normal); el resultado viaja como
   dato (`print_warning`) en el cuerpo.
   Descartado: devolver un código de error (ej. 502) cuando solo falla
   la impresión. Rompería el contrato ya establecido por 003 para esos
   mismos endpoints, y contradice RF-9 ("sin bloquear ni descartar esa
   acción").

6. **`threading.Lock()` en memoria del proceso** para serializar el
   acceso a la impresora, en vez de una cola externa.
   Descartado: Celery/RQ con Redis como broker — infraestructura extra
   que viola la regla 1 (stack mínimo); o un semáforo a nivel de base
   de datos (`select_for_update` sobre una fila "impresora"),
   innecesariamente complejo para un solo proceso con un solo recurso
   físico.

7. **Transliteración ASCII de acentos y "ñ" antes de enviar el texto a
   la impresora** (ej. "á" → "a", "ñ" → "n").
   Descartado: enviar UTF-8 crudo confiando en que la Epson TM-U220 lo
   interprete bien. Esta familia de impresoras matriciales usa páginas
   de código limitadas (CP437/860) y no soporta UTF-8 de forma
   confiable — sin esta normalización, nombres o notas con tildes
   podrían salir corruptos en el papel.

8. **El badge y el botón "Reintentar impresión" se dejan de mostrar una
   vez el pedido está cobrado o anulado**, en vez de seguir mostrando un
   indicador no accionable.
   Esto se deriva de RF-10 (el reintento ya está bloqueado en esos
   estados), pero es una decisión de este plan, no algo que la spec
   exija explícitamente: mostrar un badge sin ninguna acción posible
   solo confundiría al mesero. Descartado: seguir mostrando el badge
   igual, de forma puramente informativa.

9. **El número del día y su fecha/hora de envío se imprimen con el
   mismo tamaño de letra que el resto del ticket, sin ningún comando
   ESC/POS de tamaño o negrita**, en vez de intentar replicar en papel
   la jerarquía visual que 003-RF-14 exige en pantalla.
   La spec (003-RF-14, ya resuelta) exime explícitamente al ticket
   impreso de esa jerarquía: se imprime en texto plano de un solo estilo
   (RF-7, decisión técnica 7 de este plan). `rendering.py` solo cambia
   qué dato arma en el encabezado (`order.daily_number`/`order.sent_at`
   en vez de `order.id`) — no necesita tocar `adapters.py` ni aprender
   comandos ESC/POS nuevos.

---

## 8. Estrategia de tests

Cumpliendo la regla 6 de la constitución.

### Unitarios — `rendering.py` (sin HTTP, sin impresora)

- Maqueta exacta de cada tipo de ticket (RF-2 a RF-7): encabezado,
  metadatos, bloque de notas, lista de ítems, ajuste de línea por
  nombre largo.
- Consolidación (RF-8): un ticket "ADICIÓN" pendiente que absorbe una
  anulación antes de imprimirse muestra ambas secciones bajo el mismo
  encabezado; un ítem anulado antes de que su ticket se haya impreso
  queda completamente omitido (no aparece ni marcado "anulado").
- El primer ticket de un pedido (`desde = order.created_at`) incluye
  todos los ítems activos, aunque haya habido varias adiciones fallidas
  antes de la primera impresión exitosa.
- RF-2, 003-RF-14: el encabezado muestra `"N° {daily_number}"` + fecha de
  envío + hora del intento de impresión, nunca `order.id`; un pedido con
  `daily_number=None` (enviado antes de este cambio) imprime ese campo
  en blanco sin lanzar error; el campo de hora de envío y el de hora de
  impresión no se confunden entre sí aunque sean valores distintos del
  mismo ticket (ej. adición impresa minutos después del envío original).

### Unitarios — `services.py`

- Se dispara exactamente en: enviar (transición real, no en reenvíos
  sin efecto), adición, anulación de ítem sin auto-anular (RF-1).
- No se dispara en: crear borrador, cobrar, anular pedido completo
  (manual o automático), liberar mesa, corregir mesa, marcar entregado
  (RF-1).
- Invariante de consolidación: con un `PrintJob` `PENDING` existente, un
  evento nuevo reutiliza esa misma fila (no crea una segunda); tras un
  éxito, el siguiente evento sí crea una fila nueva.
- `retry_print`: rechaza si no es el dueño (403), si el pedido está
  cobrado/anulado (409), si no hay ticket pendiente (404); éxito limpia
  `status`/`printed_at` y dispara la notificación en tiempo real.
- Las dos categorías de error de `FakePrinterAdapter`
  (`PrinterNotDetectedError`/`PrinterFailureError`) producen el
  `print_warning` correspondiente; un fallo a mitad de impresión
  (simulado por el fake) se trata igual que un fallo total.

### Integración (`DRF APIClient` + `FakePrinterAdapter` inyectado)

- Los endpoints de 003 (enviar, agregar ítem, anular ítem) siguen
  devolviendo su mismo código de éxito de siempre, ahora con
  `print_warning` presente solo cuando el fake simula un fallo.
- El nuevo endpoint `POST /api/pedidos/{id}/reimprimir`: sus 4 casos
  (éxito, sigue fallando, 403, 404, 409).
- `has_pending_print` aparece correcto en `GET /api/pedidos/mios`,
  `/entrantes` y `/{id}`.

### Canal en tiempo real

- Un reintento exitoso notifica `pedidos.actualizado` a un admin
  conectado a `/ws/pedidos/` (reutilizando el `WebsocketCommunicator` ya
  usado en los tests de 003).

### Checklist MANUAL (con la Epson TM-U220 real conectada)

Los tests automatizados no pueden verificar hardware — esta checklist
sí:

- [ ] Enviar un pedido real imprime el ticket "PEDIDO NUEVO" completo y
      legible, con el encabezado y los ítems correctos.
- [ ] Una nota se ve claramente destacada con el marcador
      `*** NOTA ... ***` en el papel físico.
- [ ] Apagar o desconectar la impresora antes de enviar un pedido
      produce el aviso "impresora no detectada" en la pantalla del
      mesero, y el pedido queda guardado igual.
- [ ] Quitarle el papel (o provocar un atasco) produce el aviso "no se
      pudo imprimir el ticket en cocina".
- [ ] Reintentar después de resolver el problema físico imprime
      correctamente, y el badge desaparece tanto en la pantalla del
      mesero como en el panel del admin sin que el admin tenga que
      recargar la página.
- [ ] Un nombre de ítem largo se ajusta a varias líneas de forma
      legible, sin cortar ninguna palabra a mitad.
- [ ] Dos pedidos casi simultáneos (de dos meseros distintos) se
      imprimen completos y en orden, sin mezclarse ni solaparse.

---

## Cobertura de requisitos funcionales

| RF | Cubierto en |
|----|--------------|
| RF-1 | Sección 1 (llamadas desde `apps/orders/services.py`), Sección 5 (pseudocódigo `register_event_and_print`) |
| RF-2 | Sección 3 (maquetas, encabezados y metadatos, encabezado de identificación con 003-RF-14), Decisión técnica 9, Sección 8 |
| RF-3 | Sección 3 (maqueta "PEDIDO NUEVO"), Sección 5 (`desde = order.created_at` en el primer ticket) |
| RF-4 | Sección 3 (maqueta "ADICIÓN") |
| RF-5 | Sección 3 (maqueta "ANULACIÓN") |
| RF-6 | Sección 3 (bloque de notas y marcador) |
| RF-7 | Sección 3 (ancho configurable, un solo color) |
| RF-8 | Sección 2 (`PrintJob`, invariante de un solo `PENDING` por pedido), Sección 5 (pseudocódigo, derivación del contenido), Decisión técnica 2 y 3 |
| RF-9 | Sección 4 (categorías de error), Sección 5 (lock, síncrono), Sección 6 (`print_warning`), Decisión técnica 5 y 6 |
| RF-10 | Sección 2 (`PrintJob.status`), Sección 6 (endpoint de reimprimir, `has_pending_print`), Decisión técnica 8 |
| RF-11 | Sección 1 (`permissions.py` reexporta `IsOrderOwner`), Sección 6 (columna Auth/Errores del endpoint nuevo) |
