# Especificación: Impresión en cocina

## Contexto y objetivo

Cuando un mesero envía un pedido, le agrega una adición, o anula uno de
sus ítems, cocina necesita enterarse de inmediato y en papel — sin
depender de que alguien mire una pantalla. Este módulo conecta esas tres
acciones (ya existentes en
[`003-mesas-pedidos`](../003-mesas-pedidos/spec.md)) con una impresora
térmica/matriz de punto Epson TM-U220 conectada por USB al mismo equipo
donde corre el backend, y define qué pasa cuando esa impresión falla.

Depende de [`001-autenticacion-usuarios`](../001-autenticacion-usuarios/spec.md)
(sesión y roles) y de
[`003-mesas-pedidos`](../003-mesas-pedidos/spec.md) (pedidos, ítems,
notas, mesas — este módulo no crea ni modifica ninguna de esas
entidades, solo reacciona a sus eventos). Respeta las reglas 1 y 2 de
[`docs/constitution.md`](../../docs/constitution.md): la impresión no
depende de la red del restaurante ni de internet — es un periférico
local del mismo proceso. No requiere ampliar la regla 5: "reintentar
impresión" queda implícito dentro de lo que el mesero ya puede hacer
sobre sus propios pedidos.

## Usuarios

- **Mesero**: no se conecta a la impresora ni la configura; cuando envía
  un pedido, agrega una adición o anula un ítem, el ticket correspondiente
  se imprime solo, disparado por el backend. Si la impresión de uno de
  sus pedidos falla, lo ve marcado en su lista de pedidos y puede
  reintentarla cuando quiera (mientras el pedido no esté cobrado ni
  anulado).
- **Admin**: ve el mismo indicador de "no impreso" en su panel de
  pedidos entrantes, en tiempo real, como información — no reintenta la
  impresión desde ahí en este módulo.

## Historias de usuario

- Como mesero, quiero que cocina reciba automáticamente el ticket al
  enviar un pedido, para no tener que ir a avisar en persona.
- Como mesero, quiero que una adición o una anulación de ítem también se
  impriman solas, para que cocina siempre tenga la comanda al día sin que
  yo intervenga.
- Como mesero, quiero notar fácilmente si una nota de un producto
  ("sin cebolla") no se perdió entre el resto del texto del ticket.
- Como mesero, quiero enterarme de inmediato si un ticket no se pudo
  imprimir, para poder avisar a cocina de otra forma mientras se resuelve.
- Como mesero, quiero poder reintentar la impresión de un ticket que
  falló, una vez que alguien destrabó la impresora (le puso papel, la
  encendió, etc.), sin tener que recrear el pedido.
- Como mesero, si mientras un ticket sigue sin imprimirse sigo agregando
  o anulando cosas del mismo pedido, quiero que el reintento salga
  actualizado con todo eso — no quiero que cocina reciba un ticket viejo
  y otro nuevo que se contradigan o dupliquen ítems.
- Como admin, quiero ver si hay tickets sin imprimir en el panel de
  pedidos, para entender por qué cocina reclama que no le llegó algo.

## Requisitos funcionales

### RF-1 — Disparo de la impresión

- Cuando un mesero envía un pedido en "borrador" (003 RF-5) — es decir,
  cuando esa acción realmente cambia su estado a "en preparación" —, el
  sistema deberá intentar imprimir un ticket "PEDIDO NUEVO".
- Si un mesero reenvía un pedido que ya no está en "borrador" (003 RF-5
  ya trata esto como un no-op sin efecto), el sistema no deberá intentar
  imprimir nada: solo la transición real de borrador a en preparación
  dispara un intento de impresión.
- Cuando un mesero agrega una adición a un pedido ya "en preparación"
  (003 RF-5), el sistema deberá intentar imprimir un ticket "ADICIÓN".
- Cuando un mesero anula un ítem (003 RF-6) y el pedido sigue "en
  preparación" después de esa anulación, el sistema deberá intentar
  imprimir un ticket "ANULACIÓN".
- Si anular un ítem resulta en la anulación automática del pedido
  completo (porque era el último ítem activo, 003 RF-6/RF-11), entonces
  el sistema no deberá imprimir ningún ticket para esa anulación.
- El sistema nunca deberá imprimir un ticket por anular un pedido
  completo de forma manual (003 RF-11), ni por crear un borrador, cobrar,
  liberar una mesa, corregir la mesa de un pedido, o marcar/desmarcar
  "Entregado".
- La impresión siempre la dispara el backend al procesar la acción,
  nunca el dispositivo del mesero — el resultado no depende de desde qué
  celular llegó la solicitud.

### RF-2 — Encabezado y datos de cada ticket

- Todo ticket deberá llevar un encabezado con el tipo de evento que lo
  originó y el número de mesa, con el formato "PEDIDO NUEVO – Mesa N",
  "ADICIÓN – Mesa N" o "ANULACIÓN – Mesa N" según corresponda.
- Todo ticket deberá incluir además: el número de mesa, el número del
  día del pedido junto con la fecha y hora en que fue enviado
  ([003-mesas-pedidos RF-14](../003-mesas-pedidos/spec.md)) — nunca el
  identificador interno —, la hora del intento de impresión, y el
  nombre de usuario del mesero que ejecutó la acción. El número del día
  y la fecha/hora de envío se imprimen con el mismo tamaño de letra: el
  ticket queda exento de la jerarquía visual que 003-RF-14 exige en
  pantalla, al imprimirse en texto plano de un solo estilo (RF-7).
- Si el pedido no tiene número del día asignado (porque se envió antes
  de que ese requisito existiera, ver 003-mesas-pedidos RF-14), el
  sistema deberá imprimir el ticket igual, mostrando ese dato en blanco
  en su lugar — limitación transitoria y conocida, no un error.

### RF-3 — Contenido del ticket "PEDIDO NUEVO"

- El sistema deberá listar todos los ítems activos del pedido en el
  momento del envío (de catálogo o fuera de carta), cada uno con su
  cantidad y nombre.

### RF-4 — Contenido del ticket "ADICIÓN"

- El sistema deberá listar los ítems agregados desde el último ticket de
  este pedido impreso con éxito (normalmente los de una sola operación
  de adición; más de una si varias adiciones quedaron consolidadas en el
  mismo ticket pendiente, ver RF-8) — nunca el resto de ítems ya
  impresos previamente del mismo pedido.

### RF-5 — Contenido del ticket "ANULACIÓN"

- El sistema deberá mostrar los ítems anulados desde el último ticket de
  este pedido impreso con éxito (normalmente uno solo; más de uno si
  varias anulaciones quedaron consolidadas en el mismo ticket pendiente,
  ver RF-8), cada uno con su motivo de anulación — nunca el resto de
  ítems activos del pedido.

### RF-6 — Notas destacadas

- Si uno o más de los ítems incluidos en un ticket (de cualquiera de los
  3 tipos) tiene una nota (003 RF-4), el sistema deberá imprimir cada
  nota justo debajo de la línea de su propio ítem, con sangría alineada
  al nombre del ítem.
- El sistema deberá destacar cada nota envolviéndola en un marcador de
  texto en mayúsculas, con el formato `*** NOTA: texto de la nota ***`.
- Cada nota aparece una sola vez en el ticket, bajo su ítem; no hay un
  bloque de notas separado.
- Si ningún ítem incluido en el ticket tiene nota, el ticket no deberá
  llevar ninguna línea de nota.
- *(Cambio 2026-10-11: antes las notas se agrupaban al inicio del
  ticket; cocina pidió verlas junto al plato.)*

### RF-7 — Formato del ticket

- El sistema deberá imprimir siempre en texto plano, con un ancho de
  columna fijo compatible con la Epson TM-U220 (ESC/POS), compacto y
  legible (el número exacto de columnas queda definido en el plan
  técnico).
- El sistema deberá imprimir en un solo color (negro) — no usa la
  posibilidad de cinta roja de la impresora en este módulo.

### RF-8 — Consolidación de tickets pendientes

- El sistema deberá mantener como máximo un ticket pendiente (sin
  imprimir con éxito) por pedido a la vez.
- Mientras el pedido tenga un ticket pendiente, el sistema deberá
  consolidar en ese mismo ticket cualquier evento nuevo de ese pedido
  que normalmente generaría uno (otra adición, otra anulación de ítem),
  en vez de crear un ticket aparte.
- El encabezado del ticket consolidado deberá mantenerse igual al del
  evento que lo originó por primera vez (ej. si empezó como
  "PEDIDO NUEVO", sigue siendo "PEDIDO NUEVO" aunque se le consolide
  después una anulación).
- Cada intento de imprimir ese ticket pendiente (el original o un
  reintento) deberá regenerar su contenido a partir del estado actual
  de los ítems involucrados, no reimprimir un texto congelado.
- Si uno de los ítems incluidos en un ticket pendiente se anula antes de
  que ese ticket se haya impreso con éxito, el sistema deberá omitirlo
  por completo del contenido a imprimir — no deberá aparecer ni como
  línea normal ni marcado como anulado, porque cocina nunca llegó a
  verlo en papel.
- Una vez un ticket se imprime con éxito, el sistema deberá empezar
  limpio: el siguiente evento de ese pedido que lo amerite genera un
  ticket nuevo e independiente (ya no se consolida con el anterior, que
  quedó cerrado).

### RF-9 — Fallos de impresión

- El sistema deberá intentar la impresión como parte de la misma
  solicitud que originó el evento (enviar, adición o anulación), sin
  bloquear ni descartar esa acción si la impresión falla: el pedido, la
  adición o la anulación quedan guardados igual.
- Si hay más de una solicitud de impresión en cola porque la impresora
  está ocupada con otro ticket (requisito no funcional de orden), el
  sistema deberá esperar su turno antes de responder — la respuesta de
  esa acción solo se da una vez se conoce el resultado real de ese
  intento de impresión.
- Si la impresión falla, el sistema deberá devolver de inmediato, en la
  respuesta de esa misma acción, un aviso de que el ticket no se
  imprimió, distinguiendo al menos dos categorías: "impresora no
  detectada" (no se logró establecer comunicación con ella) y "error al
  imprimir" (se comunicó, pero falló por cualquier otra causa — sin
  papel, sin cinta, atasco, u otra). El sistema no está obligado a
  distinguir la causa exacta dentro de esta segunda categoría.
- Un fallo a mitad de la impresión (ej. se interrumpe después de haber
  impreso parte del ticket) deberá tratarse igual que un fallo total: el
  ticket completo queda marcado como no impreso, y un reintento
  posterior lo vuelve a imprimir entero desde el inicio.
- El sistema deberá marcar ese ticket en particular como "no impreso" de
  forma persistente, hasta que se logre imprimir con éxito.

### RF-10 — Indicador visible y reintento

- Mientras un pedido tenga un ticket marcado como "no impreso", el
  sistema deberá mostrar un único indicador visible por pedido (no uno
  por cada evento consolidado, ver RF-8) en la lista de pedidos del
  mesero dueño, y en el panel de pedidos entrantes del admin.
- El sistema deberá notificar en tiempo real después de cada intento de
  impresión (exitoso o no), no solo antes, para que ninguna pantalla se
  quede mostrando "no impreso" de un ticket que sí salió.
- El sistema deberá permitir al mesero dueño del pedido reintentar la
  impresión de ese ticket pendiente, en cualquier momento, siempre que
  el pedido no esté "cobrado" ni "anulado".
- Si el pedido ya está "cobrado" o "anulado" cuando se intenta
  reintentar, el sistema deberá rechazar la acción — igual de
  "congelado" que el resto de acciones sobre un pedido en esos estados
  (003 RF-5/RF-6/RF-7).
- Al reintentar, el sistema deberá regenerar el contenido del ticket a
  partir del estado actual del pedido y de los ítems correspondientes en
  ese momento (ver RF-8) — no reimprime un texto congelado del intento
  original.
- Si el reintento tiene éxito, el sistema deberá quitar el indicador de
  "no impreso" de ese ticket, y notificarlo en tiempo real al panel del
  admin reutilizando el mismo canal de tiempo real ya definido en
  003-mesas-pedidos para sus propios eventos.
- Si el reintento también falla, el sistema deberá mantener el
  indicador y devolver el mismo tipo de aviso descrito en RF-9.

### RF-11 — Permisos y autenticación

- El sistema deberá exigir siempre una sesión autenticada válida para el
  endpoint de reintentar impresión.
- El sistema deberá permitir reintentar la impresión de un ticket
  únicamente al mesero dueño del pedido correspondiente (003 RF-13).
- El admin puede ver el indicador de "no impreso" en su panel, pero el
  sistema no deberá ofrecerle una acción de reintentar desde ahí en este
  módulo. Sí puede reimprimir un pedido completo (RF-12).

### RF-12 — Reimpresión manual de un pedido

*(Agregado 2026-10-11: cocina necesita una copia de un pedido que ya se
imprimió bien, por ejemplo si el papel se perdió o se dañó.)*

- El sistema deberá permitir reimprimir un pedido completo:
  - al mesero dueño del pedido, mientras esté "en preparación";
  - a un admin, mientras esté "en preparación" o "cobrado" (desde
    "Pedidos entrantes" y desde la pestaña "Cobrados", 005 RF-9).
- Nunca se reimprime un pedido en "borrador" (cocina nunca lo vio) ni
  uno "anulado".
- El ticket lleva el encabezado `REIMPRESION - MESA N` con los mismos
  metadatos de RF-2, y todos los ítems activos del pedido en ese
  momento, cada uno con su nota debajo (RF-6). Los ítems anulados no
  aparecen.
- La reimpresión es una copia: no cuenta como "lo último que llegó al
  papel" para calcular el próximo ticket (RF-8), y no toca ni resuelve
  un ticket pendiente del mismo pedido.
- Si la reimpresión falla, el sistema devuelve el mismo aviso de RF-9,
  pero no deja ningún indicador de "no impreso" ni ticket pendiente: el
  usuario simplemente vuelve a intentarlo.
- Endpoint: `POST /api/pedidos/{id}/reimpresion`, con sesión
  autenticada (RF-11).

## Requisitos no funcionales

- La impresión no deberá depender de la red local ni de internet — la
  impresora está conectada por USB al mismo equipo donde corre el
  backend (constitución, reglas 1 y 2).
- Como la impresora es un recurso físico único y compartido, el sistema
  deberá garantizar que los tickets se impriman en el orden en que se
  generaron, sin solaparse, aunque lleguen solicitudes de distintos
  meseros casi al mismo tiempo — una solicitud puede tener que esperar
  su turno antes de que el sistema le confirme el resultado (RF-9).

## Casos límite

- Un pedido tiene notas en más de un ítem → cada nota aparece debajo de
  su propio ítem (RF-6).
- Se anula el último ítem activo de un pedido (auto-anulación del pedido
  completo, 003 RF-6/RF-11) → no se imprime ningún ticket (RF-1).
- Se anula un pedido completo de forma manual (003 RF-11) → no se
  imprime ningún ticket (RF-1).
- La impresora se queda sin papel a mitad de un turno con varios pedidos
  en cola → cada pedido mantiene su propio ticket pendiente
  independiente, con su propio indicador y botón de reintentar (RF-8,
  RF-10); dentro de un mismo pedido, los fallos sucesivos se consolidan
  en un único ticket pendiente, no se acumulan varios.
- El mesero agrega o anula ítems de un pedido mientras su ticket sigue
  sin imprimir → todo se consolida en ese mismo ticket pendiente, con el
  encabezado del evento original; los ítems anulados antes de imprimir
  se omiten por completo (RF-8).
- Dos meseros envían pedidos casi al mismo tiempo → ambos tickets se
  imprimen, en el orden en que el backend procesó cada solicitud, sin
  mezclarse ni perderse; la segunda solicitud puede tardar un poco más
  en responder mientras espera su turno (Requisitos no funcionales,
  RF-9).
- Un ítem fuera de carta con nota también sigue la misma regla de
  destacado que uno de catálogo (RF-6).
- La impresora falla a mitad de un ticket, dejando un papel parcial →
  se trata como fallo total; el reintento reimprime el ticket completo
  desde el inicio (RF-9).
- El mesero dueño de un pedido con un ticket pendiente es desactivado
  (001) antes de reintentar → el ticket queda sin ninguna vía de
  reintento dentro del sistema; es una limitación conocida de esta
  versión (ver "Fuera de alcance").
- Dos ítems fuera de carta con el mismo nombre (003 permite nombres
  repetidos) tienen notas distintas en el mismo ticket → el marcador de
  nota no los distingue entre sí; es una limitación conocida aceptada
  (ver "Fuera de alcance").
- El texto libre de una nota contiene literalmente "***" → puede
  confundirse visualmente con el marcador de destacado; es una
  limitación conocida aceptada (ver "Fuera de alcance").
- Se reintenta imprimir un ticket cuyo pedido ya fue cobrado o anulado
  por completo desde el intento original → el sistema rechaza el
  reintento (RF-10).
- Se imprime (o reintenta imprimir) el ticket de un pedido sin número
  del día, por haberse enviado antes de que existiera ese requisito
  (003-mesas-pedidos RF-14) → se imprime igual, con ese dato en blanco
  (RF-2); limitación transitoria, desaparece sola conforme esos pedidos
  se van cobrando o anulando.

## Fuera de alcance

- La lógica de crear/editar pedidos, agregar ítems, adiciones y
  anulaciones — ya cubierta por 003-mesas-pedidos. Este módulo solo
  reacciona a esos eventos.
- El cobro de un pedido (003 RF-9).
- Imprimir algo cuando se anula un pedido completo (manual o
  automático) — queda explícitamente fuera (RF-1).
- El uso de la cinta roja de la impresora / impresión a dos colores —
  por ahora todo se imprime en un solo color; queda como posible mejora
  futura.
- Selección o configuración de múltiples impresoras — se asume una
  única impresora fija conectada por USB al equipo del backend.
- Reintentos automáticos o reimpresión programada — el único mecanismo
  de reintento es manual, iniciado por el mesero (RF-10).
- Que el admin pueda reintentar la impresión desde su panel — en este
  módulo es de solo lectura para el admin (RF-11).
- Distinguir causas de fallo más allá de "impresora no detectada" vs.
  "error al imprimir" (ej. diferenciar sin papel de sin cinta) (RF-9).
- Que un admin pueda reintentar la impresión de un ticket cuyo mesero
  dueño fue desactivado — queda como limitación conocida de esta
  versión, a resolver en una futura iteración si hace falta (ver Casos
  límite).
- Distinguir en el papel dos ítems fuera de carta con el mismo nombre
  que tengan notas distintas — limitación conocida aceptada (ver Casos
  límite).
- Escapar o reemplazar asteriscos que el mesero escriba dentro del
  texto libre de una nota — limitación conocida aceptada (ver Casos
  límite).
- Ampliar la regla 5 de la constitución — "reintentar impresión" queda
  implícito dentro de lo que el mesero ya puede hacer sobre sus propios
  pedidos, sin necesitar una enumeración aparte.

## Criterios de finalización

- Enviar un pedido con al menos un ítem imprime un ticket
  "PEDIDO NUEVO – Mesa N" con todos sus ítems activos, y las notas (si
  las hay) destacadas al inicio con el marcador `*** NOTA ... ***`.
- Reenviar un pedido que ya no está en "borrador" no intenta imprimir
  nada de nuevo.
- Agregar una adición a un pedido en preparación imprime (o consolida en
  el ticket pendiente de ese pedido) un ticket "ADICIÓN" con únicamente
  los ítems nuevos desde el último ticket impreso con éxito.
- Anular un ítem (sin que sea el último activo) imprime (o consolida)
  un ticket "ANULACIÓN" con únicamente los ítems anulados desde el
  último ticket impreso con éxito, cada uno con su motivo.
- Anular el último ítem activo de un pedido (auto-anulación) no imprime
  ningún ticket.
- Anular un pedido completo de forma manual no imprime ningún ticket.
- Mientras un ticket de un pedido siga sin imprimir, cualquier adición o
  anulación posterior de ese mismo pedido se consolida en ese único
  ticket pendiente, con el encabezado del evento que lo originó, y
  omitiendo del todo cualquier ítem que se haya anulado antes de
  imprimir.
- Un fallo de impresión nunca pierde el pedido ni bloquea la acción del
  mesero: la acción queda guardada, el mesero recibe un aviso inmediato
  (distinguiendo al menos "impresora no detectada" de "error al
  imprimir"), y mientras el ticket no se haya impreso con éxito queda
  marcado con un único indicador visible por pedido, tanto en la lista
  de pedidos del mesero como en el panel de pedidos entrantes del admin
  (actualizado en tiempo real).
- El mesero dueño del pedido puede reintentar la impresión de un ticket
  marcado como "no impreso" mientras el pedido no esté cobrado ni
  anulado, y el contenido se regenera con el estado actual del
  pedido/ítems, no con un texto congelado.
- Ningún endpoint de este módulo funciona sin sesión autenticada, y solo
  el mesero dueño de un pedido puede reintentar la impresión de sus
  propios tickets.
- Todo ticket muestra el número del día del pedido (con su fecha/hora de
  envío) en vez del identificador interno, que nunca aparece en papel.

## Dudas abiertas

Ninguna pendiente. De la ronda inicial de dudas, quedaron resueltas y ya
incorporadas al texto:

- Las "notas del pedido" que menciona el brief son las notas por ítem ya
  existentes en 003 (RF-4) — no se agrega ningún campo de nota nuevo a
  nivel de pedido completo (RF-6).
- Anular un pedido completo (manual o automático por quedarse sin ítems
  activos) nunca imprime un ticket (RF-1).
- Por ahora la impresora se usa en un solo color; la distinción de notas
  se logra con un marcador de texto en mayúsculas, no con color (RF-6,
  RF-7).
- Los encabezados son "PEDIDO NUEVO", "ADICIÓN" y "ANULACIÓN", seguidos
  de " – Mesa N" (RF-2).
- Cada ticket lleva mesa, id de pedido, hora y usuario del mesero como
  metadatos (RF-2).
- El aviso de fallo de impresión es inmediato (en la respuesta de la
  misma acción) y además deja un indicador persistente visible hasta que
  se imprima con éxito (RF-9, RF-10).
- El reintento de impresión es manual, exclusivo del mesero dueño del
  pedido, y regenera el contenido con el estado actual en vez de
  reimprimir un texto congelado (RF-10).
- El admin ve el indicador de "no impreso" en su panel de pedidos
  entrantes en tiempo real, pero no tiene una acción de reintentar ahí
  (RF-10, RF-11).

De la revisión de QA posterior, quedaron resueltas y ya incorporadas:

- Reenviar un pedido que ya no está en "borrador" no dispara un nuevo
  intento de impresión (RF-1).
- Mientras un pedido tenga un ticket sin imprimir, los eventos nuevos
  (adiciones, anulaciones) se consolidan en ese mismo ticket pendiente
  en vez de generar uno aparte — el encabezado queda fijo desde el
  primer evento, y el contenido se regenera con el estado actual cada
  vez que se intenta imprimir (RF-8).
- Un ítem anulado antes de que su ticket se haya impreso se omite por
  completo del contenido — nunca aparece marcado como "anulado" en
  papel, porque cocina nunca llegó a verlo (RF-8).
- El indicador de "no impreso" es uno solo por pedido, no uno por cada
  evento consolidado (RF-10).
- El aviso de fallo distingue al menos "impresora no detectada" de
  "error al imprimir", sin comprometerse a diferenciar causas más
  específicas como sin papel vs. sin cinta (RF-9).
- Un fallo a mitad de la impresión se trata igual que un fallo total:
  el reintento reimprime el ticket completo desde el inicio (RF-9).
- Una vez el pedido está cobrado o anulado, ya no se puede reintentar
  la impresión de ningún ticket pendiente suyo (RF-10) — esto también
  resuelve la tensión con el panel de "pedidos entrantes" del admin
  (003), que ya excluye pedidos cobrados/anulados: para entonces el
  ticket ya no es accionable de todas formas.
- Si hay que esperar el turno de la impresora porque está ocupada con
  otro ticket, la respuesta de esa acción espera a conocer el resultado
  real antes de confirmarse — no se declara éxito/fallo sin saberlo
  (RF-9).
- Un reintento exitoso se notifica en tiempo real al panel del admin,
  reutilizando el mismo canal de WebSocket que ya usa 003-mesas-pedidos
  para sus propios eventos (RF-10).
- No se amplía la regla 5 de la constitución: "reintentar impresión"
  queda implícito dentro de lo que el mesero ya puede hacer sobre sus
  propios pedidos.
- Quedan como limitaciones conocidas y aceptadas, sin una regla
  especial: un ticket pendiente de un mesero luego desactivado (nadie
  puede reintentarlo), dos ítems fuera de carta con el mismo nombre y
  notas distintas en el mismo ticket, y el texto libre de una nota que
  contenga literalmente "***" (ver "Fuera de alcance").

De la ronda de "número del día" (nuevo requisito posterior, ver
003-mesas-pedidos RF-14), quedaron resueltas y ya incorporadas:

- El ticket muestra el número del día del pedido junto con la fecha y
  hora de envío, nunca el identificador interno (RF-2).
- Un pedido sin número del día (enviado antes de este cambio) igual se
  imprime, mostrando ese dato en blanco — limitación transitoria, no un
  error (RF-2).

De la auditoría QA posterior sobre el "número del día", quedó resuelto
y ya incorporado:

- El ticket impreso queda exento de la jerarquía visual entre número y
  fecha/hora que 003-RF-14 exige en pantalla: ambos se imprimen con el
  mismo tamaño de letra, al ser texto plano de un solo estilo (RF-2,
  RF-7).

> **Nota (2026-10-12):** el comprobante para el cliente
> ([005-cobro RF-11](../005-cobro/spec.md)) usa esta misma impresora y el
> mismo lock de impresión, para que nunca se mezcle con un ticket de
> cocina, pero no es un `PrintJob`: no se consolida, no se reintenta ni
> marca "No impreso en cocina".
