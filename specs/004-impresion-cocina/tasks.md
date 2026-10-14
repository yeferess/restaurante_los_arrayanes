# 004 · Impresión en cocina — Tareas

Basado en `spec.md` (requisitos) y `plan.md` (diseño técnico). Cada tarea
es de ~20-30 min, están en orden de dependencia (no empezar una tarea sin
que las anteriores estén hechas). Cada una indica el/los RF que cubre y
una condición verificable de "Hecho cuando".

---

## Fase 0 — Setup del módulo

- [x] **T01 — Crear la app `kitchen_printing`**
  RF: — (infraestructura)
  Hecho cuando: existe `apps/kitchen_printing/` con la estructura del
  plan (sección 1), está en `INSTALLED_APPS`, y `python manage.py check`
  no reporta errores.

- [x] **T02 — Registrar `urls.py` del módulo**
  RF: — (infraestructura)
  Hecho cuando: `config/urls.py` incluye `apps.kitchen_printing.urls`
  bajo `/api/`, y una request a una ruta aún no implementada devuelve
  404 (no 500 ni error de importación).

---

## Fase 1 — Modelo de datos

- [x] **T03 — Modelo `PrintJob`**
  RF: RF-8, RF-9, RF-10
  Hecho cuando: existe el modelo con `order` (FK `PROTECT` a
  `orders.Order`), `ticket_type` (choices `NEW_ORDER`/`ADDITION`/
  `VOID`), `status` (choices `PENDING`/`PRINTED`, default `PENDING`),
  `attempts` (`PositiveIntegerField`, default `1`), `created_at`,
  `printed_at` (nullable), y la migración aplica sin errores.

---

## Fase 2 — Adaptador de impresora

- [x] **T04 — Excepciones e interfaz `PrinterAdapter`**
  RF: RF-9
  Hecho cuando: existen `PrinterNotDetectedError` y
  `PrinterFailureError` (heredan de una excepción base común), y una
  clase abstracta `PrinterAdapter` con el método
  `print_ticket(text: str)`.

- [x] **T05 — `FakePrinterAdapter` (doble de test)**
  RF: RF-9 (soporte de tests)
  Hecho cuando: implementa `PrinterAdapter`; se puede configurar para
  simular éxito, `PrinterNotDetectedError` o `PrinterFailureError` en
  cada llamada; registra cuántas veces se llamó y con qué texto exacto,
  para usarlo en aserciones.

- [x] **T06 — `get_printer_adapter()` y configuración**
  RF: RF-9 (soporte), regla 1 de la constitución
  Hecho cuando: una función de fábrica devuelve el adaptador real o el
  fake según un ajuste de `settings.py`; los tests lo sobreescriben con
  `FakePrinterAdapter` sin tocar ninguna impresora real;
  `KITCHEN_PRINTER_COLUMNS = 40` existe en `settings.py`.

- [x] **T07 — `EscposUsbPrinterAdapter` (real, Windows)**
  RF: RF-9, plan sección 4
  Hecho cuando: usa `win32print` para enviar el texto como trabajo RAW
  a la impresora configurada por nombre; traduce "impresora no
  encontrada/offline" a `PrinterNotDetectedError`, y cualquier otro
  fallo del spooler a `PrinterFailureError`. (No se puede testear
  automáticamente sin la impresora real — ver T36.)

---

## Fase 3 — Rendering de tickets

- [x] **T08 — Encabezado y metadatos básicos**
  RF: RF-2
  Hecho cuando: `build_ticket_text` produce un encabezado
  `"<TIPO> - MESA <N>"`, seguido de `Pedido #<id>`, fecha/hora, y
  `Mesero: <username>`, todo dentro del ancho de
  `KITCHEN_PRINTER_COLUMNS`.

- [x] **T09 — Transliteración ASCII**
  RF: plan, decisión técnica 7
  Hecho cuando: una función convierte tildes y "ñ" a su equivalente
  ASCII (á→a, ñ→n, etc.) antes de insertar cualquier texto (nombre,
  nota, motivo) en el ticket.

- [x] **T10 — Ajuste de línea con sangría colgante**
  RF: RF-7
  Hecho cuando: una línea de ítem que excede el ancho configurado se
  parte con `textwrap`, y las líneas siguientes quedan alineadas con
  una sangría de 4 espacios, sin cortar ninguna palabra a mitad.

- [x] **T11 — Notas destacadas bajo su ítem**
  RF: RF-6
  Hecho cuando: cada nota aparece justo debajo de la línea de su ítem,
  con sangría alineada al nombre, con el formato
  `*** NOTA: <texto> ***` en mayúsculas; si ningún ítem tiene nota, no
  aparece ninguna línea de nota. (Rehecho 2026-10-11: antes iban
  agrupadas al inicio.)

- [x] **T12 — Contenido "PEDIDO NUEVO"**
  RF: RF-3
  Hecho cuando: para `ticket_type=NEW_ORDER` sin impresiones previas
  exitosas de ese pedido, el ticket lista todos los ítems activos
  (cantidad + nombre), de catálogo o fuera de carta.

- [x] **T13 — Contenido derivado "desde el último impreso"**
  RF: RF-4, RF-5, RF-8
  Hecho cuando: `build_ticket_text` calcula la referencia a partir del
  último `PrintJob` `PRINTED` de ese pedido (sus marcas `last_item_id`/
  `last_action_id`, o `0`/`0` si no hay ninguno), y arma dos secciones
  posibles — ítems agregados (`OrderItem.id > last_item_id`, no
  anulados) e ítems anulados (`OrderAction` tipo `ITEM_VOIDED` con
  `id > last_action_id`) — cada una solo aparece si tiene contenido.
  Nota de implementación: se usa el id autoincremental como referencia
  en vez del timestamp — dos filas creadas en el mismo instante pueden
  empatar en timestamp (confirmado con un script de depuración contra
  la base de datos de test en memoria) pero nunca en id.

- [x] **T14 — Omitir ítems anulados antes de la primera impresión**
  RF: RF-8
  Hecho cuando: si un ítem se agregó y se anuló, ambos después de
  `desde`, y el ticket nunca se imprimió con éxito en el medio, ese
  ítem no aparece en ninguna sección (ni como agregado ni como
  anulado).

---

## Fase 4 — Servicios: consolidación e impresión

- [x] **T15 — `register_event_and_print()`: consolidación**
  RF: RF-8
  Hecho cuando: si ya existe un `PrintJob` `PENDING` para el pedido, lo
  reutiliza (no crea uno nuevo, sin importar el tipo de evento
  recibido); si no existe uno, crea uno nuevo con
  `ticket_type=event_type`.

- [x] **T16 — `register_event_and_print()`: intento e impresión**
  RF: RF-9
  Hecho cuando: llama al adaptador con el texto regenerado (Fase 3),
  incrementa `attempts`; si tiene éxito marca `status=PRINTED` y
  `printed_at=now()` y devuelve `print_warning=None`; si falla, deja
  `status=PENDING` y devuelve el mensaje correspondiente según la
  excepción (impresora no detectada vs. error al imprimir).

- [x] **T17 — Serialización con `threading.Lock()`**
  RF: Requisitos no funcionales (orden, sin solapar)
  Hecho cuando: un test con hilos/mocks confirma que dos llamadas
  concurrentes a `register_event_and_print`/`retry_print` nunca
  ejecutan `adapter.print_ticket` al mismo tiempo.

- [x] **T18 — `retry_print()`**
  RF: RF-9, RF-10, RF-11
  Hecho cuando: rechaza si el mesero no es el dueño del pedido,
  rechaza si el pedido está `CHARGED` o `VOIDED`, rechaza si no hay
  ningún `PrintJob` `PENDING`; si lo hay, reintenta con la lógica de
  T15/T16 y, si tiene éxito, deja lista la notificación en tiempo real
  (Fase 7).

---

## Fase 5 — Integración con `apps.orders`

- [x] **T19 — Hook en `send_order()`**
  RF: RF-1
  Hecho cuando: tras la transición real de "borrador" a "en
  preparación" se llama a `register_event_and_print(order, NEW_ORDER)`;
  un reenvío sin efecto no la llama.

- [x] **T20 — Hook en `add_item()`**
  RF: RF-1
  Hecho cuando: solo en la rama `line_type == ADDITION` se llama a
  `register_event_and_print(order, ADDITION)`; agregar un ítem en
  "borrador" (`ORIGINAL`) no la llama.

- [x] **T21 — Hook en `void_item()`**
  RF: RF-1
  Hecho cuando: se llama a `register_event_and_print(order, VOID)`
  solo si el pedido sigue "en preparación" después de la anulación; si
  el pedido se auto-anuló por completo, no se llama.

---

## Fase 6 — Endpoints y contrato de API

- [x] **T22 — `POST /api/pedidos/{id}/reimprimir`**
  RF: RF-9, RF-10, RF-11
  Hecho cuando: el dueño del pedido recibe 200 con `print_warning`
  (null o mensaje) según el resultado; 403 si no es el dueño; 404 si
  el pedido no existe o no hay ticket pendiente; 409 si el pedido ya
  está cobrado o anulado.

- [x] **T23 — `print_warning` en enviar/agregar ítem/anular ítem**
  RF: RF-9
  Hecho cuando: las respuestas de `POST /api/pedidos/{id}/enviar`,
  `POST /api/pedidos/{id}/items` (pedido ya en preparación) y
  `POST /api/pedidos/{id}/items/{item_id}/anular` incluyen
  `print_warning` (null si imprimió bien o si no correspondía
  imprimir), sin cambiar su código de éxito habitual.

- [x] **T24 — `has_pending_print` en las lecturas de pedidos**
  RF: RF-10
  Hecho cuando: `GET /api/pedidos/mios`, `GET /api/pedidos/entrantes` y
  `GET /api/pedidos/{id}` incluyen `has_pending_print` (true si existe
  un `PrintJob` `PENDING` para ese pedido).

- [x] **T25 — Permisos del endpoint de reimprimir**
  RF: RF-11
  Hecho cuando: `apps/kitchen_printing/permissions.py` reexporta
  `IsOrderOwner` de `apps.orders`, y la vista de T22 la usa igual que
  el resto de endpoints de pedido de 003.

---

## Fase 7 — Tiempo real

- [x] **T26 — Notificación en tiempo real al reimprimir con éxito**
  RF: RF-10
  Hecho cuando: un admin conectado a `/ws/pedidos/` recibe
  `pedidos.actualizado` cuando un reintento de impresión tiene éxito;
  no lo recibe si el reintento vuelve a fallar.

---

## Fase 8 — Tests de integración

- [x] **T27 — Integration tests del endpoint de reimprimir (T22)**
  RF: RF-9, RF-10, RF-11
  Hecho cuando: cada código de respuesta (200 éxito, 200 con aviso de
  fallo, 403, 404, 409) tiene al menos un test, y todos pasan.

- [x] **T28 — Integration tests de disparo desde los endpoints de 003**
  RF: RF-1, RF-9
  Hecho cuando: enviar, agregar ítem (adición) y anular ítem disparan
  el intento de impresión correcto, y su respuesta incluye
  `print_warning` según el resultado simulado por `FakePrinterAdapter`.

- [x] **T29 — Integration test: consolidación completa**
  RF: RF-8
  Hecho cuando: un test reproduce: falla el ticket de "PEDIDO NUEVO" →
  se agrega una adición (sin crear un segundo `PrintJob`) → se anula
  uno de los ítems agregados antes de reintentar (no aparece en el
  contenido regenerado) → se reintenta con éxito → el siguiente evento
  sí crea un `PrintJob` nuevo.

- [x] **T30 — Integration test: flujo completo con fallo y reintento**
  RF: RF-1, RF-8, RF-9, RF-10
  Hecho cuando: un test end-to-end reproduce enviar pedido con
  impresora simulada en fallo → `has_pending_print=true` → reintentar
  con éxito → `has_pending_print=false` y notificación en tiempo real
  al admin.

- [x] **T31 — Tests de permisos y autenticación**
  RF: RF-11
  Hecho cuando: el endpoint de reimprimir tiene un test que confirma
  401 sin sesión, y 403 para un mesero que no es el dueño del pedido.

---

## Fase 9 — Frontend

- [x] **T32 — `retryPrint()` en `lib/api/orders.ts`**
  RF: RF-10
  Hecho cuando: existe `retryPrint(orderId): Promise<Order>` que llama
  a `POST /api/pedidos/{id}/reimprimir`, propagando el error tal cual
  lo devuelve la API; el tipo `Order` gana `has_pending_print:
  boolean`, y `sendOrder`/`addItem`/`voidItem` devuelven también
  `print_warning`.

- [x] **T33 — Badge y botón de reintento en "Mis pedidos"**
  RF: RF-9, RF-10
  Hecho cuando: `MyOrdersList.tsx` muestra un indicador "No impreso en
  cocina" y un botón "Reintentar impresión" cuando `has_pending_print`
  es `true` y el pedido no está cobrado ni anulado; al tocar el botón
  llama a `retryPrint` y refresca el indicador.

- [x] **T34 — Badge de solo lectura en "Pedidos entrantes" (admin)**
  RF: RF-10
  Hecho cuando: `IncomingOrdersPanel.tsx` muestra el mismo indicador
  cuando `has_pending_print` es `true`, sin ningún botón de acción, y
  se actualiza solo al recibir el evento de tiempo real existente.

- [x] **T35 — Aviso inmediato de fallo al enviar/agregar/anular**
  RF: RF-9
  Hecho cuando: si la respuesta de enviar pedido, agregar ítem o
  anular ítem trae `print_warning` no nulo, `OrderBuilder.tsx` muestra
  ese mensaje de inmediato junto con la confirmación de la acción.

---

## Fase 10 — Verificación manual

- [ ] **T36 — Checklist manual con la impresora real**
  RF: RF-2 a RF-10 (verificación de hardware)
  Hecho cuando: se completan los 7 puntos de la checklist manual del
  plan (sección 8) con la Epson TM-U220 física conectada, y se
  documenta el resultado de cada uno.

---

## Fase 11 — Número del día (RF-2, 003-RF-14)

- [x] **T37 — Encabezado muestra el número del día, no el id**
  RF: RF-2, 003-RF-14
  Hecho cuando: `build_ticket_text` arma el encabezado con `"N°
  {order.daily_number}"` + la fecha/hora de `order.sent_at`, y conserva
  por separado la hora del intento de impresión (ya existente desde
  T08) sin que ambas marcas de tiempo se confundan en el texto; ninguna
  línea del ticket usa `order.id`.

- [x] **T38 — Campo en blanco para pedidos sin número del día**
  RF: RF-2, 003-RF-14
  Hecho cuando: un pedido con `daily_number=None` (enviado antes de
  desplegar 003-RF-14) imprime ese campo en blanco, sin lanzar una
  excepción ni mostrar literalmente `"None"`.

- [x] **T39 — Unit tests del encabezado con número del día (T37, T38)**
  RF: RF-2
  Hecho cuando: cubren el encabezado con un `daily_number` real, con
  `daily_number=None`, y un caso con fecha de envío distinta a la hora
  del intento de impresión (ej. una adición impresa minutos después del
  envío original) confirmando que no se mezclan; todos pasan.

- [x] **T40 — Reimpresión manual de un pedido**
  RF: RF-12
  Hecho cuando: `POST /api/pedidos/{id}/reimpresion` imprime
  `REIMPRESION - MESA N` con todos los ítems activos y sus notas; lo
  permite al dueño (en preparación) y al admin (en preparación o
  cobrado); rechaza borrador/anulado (409) y a otro mesero (403); un
  fallo no deja ticket pendiente; no mueve `_since_reference`; botón
  "Reimprimir" en `MyOrdersList`, `IncomingOrdersPanel` y
  `ChargedOrdersPanel`. Tests en `test_reprint.py`.

- [x] **T41 — Aviso en tiempo real después de imprimir**
  RF: RF-10
  Hecho cuando: `register_event_and_print` notifica al terminar el
  intento, y un test confirma que la notificación llega con el ticket
  ya en `PRINTED` (sin "No impreso" falso).

- [x] **T42 — "Imprimir pedido" como paso aparte**
  RF: RF-1, RF-8, RF-10
  Hecho cuando: `print_order` + `POST /api/pedidos/{id}/imprimir` (y
  `/reimprimir` como alias del reintento) envía las adiciones pendientes
  e imprime un solo ticket con lo que falta en papel, con el encabezado
  que corresponde; rechaza si no hay nada nuevo (409), a otro mesero
  (403) y pedidos cerrados (409); crear, agregar y anular ya no imprimen;
  `has_unprinted_changes` en la respuesta del mesero; `OrderBuilder`
  muestra "Imprimir pedido" / "Todo impreso" y `MyOrdersList` "Sin
  imprimir" e "Imprimir pedido" ("Reimprimir pedido" pasa a "Reimprimir
  copia"). Tests en `test_crear_e_imprimir_aparte.py` y los tests de 004
  actualizados.

- [x] **T43 — Encabezado "MOSTRADOR"**
  RF: RF-2
  Hecho cuando: el encabezado usa `table_label` y un pedido sin mesa
  imprime "PEDIDO NUEVO - MOSTRADOR". Tests en
  `test_pedido_admin_mostrador.py`.

- [x] **T44 — Una NOTA por renglón**
  RF: RF-6
  Hecho cuando: `format_note_lines` imprime un `*** NOTA ***` por cada
  renglón de la nota (ticket nuevo, adición, anulación y reimpresión).
  Tests en `test_merge_repeated_items.py`.
