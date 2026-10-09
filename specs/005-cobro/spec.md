# Especificación: Cobro

## Contexto y objetivo

Cuando el cliente se acerca a caja, el admin necesita registrar el pago
de su pedido desde el panel de escritorio: cuánto se cobró, con qué
opción de pago, y dejar constancia de quién lo procesó y cuándo. Este
módulo cubre ese registro, el consolidado que el admin ve antes de
confirmar, y cómo se corrige un cobro mal registrado sin perder el
rastro de lo que pasó.

Depende de [`001-autenticacion-usuarios`](../001-autenticacion-usuarios/spec.md)
(sesión y roles) y de [`003-mesas-pedidos`](../003-mesas-pedidos/spec.md)
(pedidos, ítems, mesas — este módulo no crea ni modifica esas
entidades, salvo los cambios de estado que ya definía 003 al cobrar:
pedido → "cobrado", mesa → "pagada"). Extiende el cobro que 003 ya
dejaba previsto (RF-9: cobrar la mesa de un pedido en preparación,
admin-only) agregándole la opción de pago elegida y la posibilidad de
corregirlo. Respeta — y **amplía explícitamente** — las reglas 4 y 5 de
[`docs/constitution.md`](../../docs/constitution.md): anular un cobro
se suma al grupo de acciones que exigen quién, cuándo y por qué (regla
4), y "anula un cobro" / "gestiona el catálogo de cuentas de pago" se
suman a las acciones exclusivas de admin (regla 5). Ningún cobro, y
ninguna cuenta del catálogo, se edita o se borra una vez creado o usado
— la única corrección posible es anular y volver a cobrar.

Este módulo también debe preservar un invariante que 003 ya daba por
sentado (RF-2 de 003): **una mesa ocupada tiene siempre un único pedido
activo**. Corregir un cobro revive un pedido (lo vuelve a "en
preparación"), así que el diseño de esa corrección debe garantizar que
nunca se rompa ese invariante (ver RF-6).

## Usuarios

- **Admin**: la única persona que cobra pedidos, corrige cobros mal
  registrados, y administra el catálogo de opciones de pago (crear
  cuentas, eliminar las que nunca se usaron).
- **Mesero**: no interviene en este módulo. No cobra, no ve el catálogo
  de opciones de pago, y no puede corregir un cobro — solo nota que su
  pedido pasó a "cobrado" (o que volvió a "en preparación" si el admin
  corrigió un cobro por error), igual que con cualquier otro cambio de
  estado ya cubierto por 003.

## Historias de usuario

- Como admin, quiero registrar el cobro de un pedido eligiendo con qué
  se pagó (efectivo o una de mis cuentas), para llevar la caja al día.
- Como admin, quiero ver el total correcto del pedido (con sus
  adiciones y sin sus ítems anulados) antes de confirmar el cobro, para
  no cobrar de más ni de menos.
- Como admin, quiero poder corregir un cobro si me equivoqué de opción
  de pago o cobré el pedido equivocado, sin que el error quede oculto
  ni se pierda el registro de lo que pasó.
- Como admin, quiero armar y mantener la lista de cuentas donde puedo
  recibir pagos (Nequi, cuentas bancarias, etc.), para no tener que
  escribirlas a mano cada vez.
- Como admin, quiero que una cuenta que ya usé en algún cobro no se
  pueda borrar por accidente, para no perder de dónde vino ese pago.
- Como admin, si dos personas en caja intentan cobrar el mismo pedido
  casi al mismo tiempo por error, quiero que el sistema lo impida en
  vez de duplicar el cobro.

## Requisitos funcionales

### RF-1 — Quién cobra y cuándo

- Cobrar un pedido deberá ser una acción exclusiva del rol admin — el
  mesero nunca cobra.
- El sistema deberá permitir cobrar un pedido en cualquier momento
  mientras su mesa esté "ocupada" (003, `Table.Status.OCCUPIED`), sin
  importar si el pedido ya se marcó como entregado o no (003 RF-8). No
  existe un estado intermedio de "por cobrar".
- El sistema no deberá permitir cobrar un pedido que esté en "borrador",
  ya "cobrado", o "anulado" — mismo criterio que el cobro ya definido en
  003 (RF-9).
- Si dos solicitudes de cobro del mismo pedido llegan casi al mismo
  tiempo (condición de carrera), el sistema deberá procesar solo la
  primera y rechazar la segunda con un error indicando que el pedido ya
  fue cobrado — nunca deberá crear dos cobros activos para el mismo
  pedido.

### RF-2 — Catálogo de opciones de pago

- El sistema deberá ofrecer una única lista de opciones de pago para
  elegir al cobrar — no un campo de "método de pago" separado de uno de
  "cuenta".
- Esa lista deberá incluir siempre una opción fija, "Efectivo", que el
  sistema no deberá permitir crear de nuevo ni eliminar.
- El admin deberá poder agregar a esa lista cuentas propias (ej.
  "Nequi #1234", "Bancolombia Ahorros"), cada una identificada por un
  nombre de texto no vacío.
- El sistema no deberá permitir crear una cuenta con el mismo nombre
  que una ya existente (incluyendo "Efectivo") — los nombres del
  catálogo deberán ser siempre únicos.
- El sistema no deberá permitir editar el nombre de una cuenta ya
  creada — si el admin se equivocó al escribirlo, deberá eliminarla (si
  nunca se usó, ver siguiente punto) y crear una nueva con el nombre
  correcto.
- El sistema deberá permitir eliminar una cuenta únicamente si ningún
  cobro la ha usado nunca (incluyendo cobros ya anulados, ver RF-6); si
  al menos un cobro la usó alguna vez, el sistema deberá rechazar la
  eliminación.

### RF-3 — Registrar un cobro

- Al cobrar, el sistema deberá exigir que el admin elija exactamente una
  opción de la lista del catálogo (RF-2) — no deberá permitir confirmar
  un cobro sin ninguna opción elegida.
- El sistema deberá guardar, de forma permanente e inmutable, al
  confirmar un cobro: el pedido, la opción de pago elegida, el monto
  exacto cobrado (ver RF-4), el admin que lo procesó, y la fecha y hora.
- El monto guardado deberá quedar fijo en ese instante (no deberá
  recalcularse después a partir de cambios posteriores en el pedido).
- La venta deberá seguir atribuida siempre al mesero dueño del pedido —
  quien lo creó originalmente (003 RF-2) —, nunca al admin que la
  cobró; esto ya se deriva del pedido mismo, sin necesitar un campo
  adicional.

### RF-4 — Consolidado visible al cobrar

- Antes de confirmar un cobro, el sistema deberá mostrar al admin el
  total del pedido ya calculado — la suma de sus ítems activos
  (pedido original más adiciones, sin los ítems anulados), igual
  cálculo que el total que 003 ya expone en el detalle de un pedido.
- El sistema no deberá requerir un desglose adicional agrupado por
  "pedido original / adiciones / anulado" — el total consolidado y el
  listado de ítems ya existentes son suficientes.

### RF-5 — Efecto de confirmar el cobro

- Al confirmar un cobro, el sistema deberá pasar el pedido a "cobrado"
  (`Order.Status.CHARGED`) y la mesa a "pagada" (`Table.Status.PAID`) —
  mismo efecto que el cobro ya definido en 003 (RF-9).
- El sistema no deberá liberar la mesa automáticamente al cobrar —
  liberarla sigue siendo una acción aparte, del mesero, una vez el
  cliente se retira (003 RF-10).
- Mientras el pedido esté "cobrado", el sistema no deberá permitir
  agregarle ni anularle ítems — ya garantizado por las validaciones
  existentes de 003.

### RF-6 — Corrección de un cobro por error

- El sistema no deberá permitir editar ni borrar un cobro ya confirmado
  bajo ninguna circunstancia. La única forma de corregirlo deberá ser
  anularlo.
- El sistema deberá permitir a cualquier admin (no exclusivamente a
  quien lo registró) anular un cobro activo, exigiendo siempre un
  motivo de texto obligatorio.
- El sistema no deberá permitir anular un cobro que ya esté anulado.
- **El sistema no deberá permitir anular un cobro si, para ese momento,
  la mesa del pedido ya tiene otro pedido distinto activo** ("borrador"
  o "en preparación") — es decir, si la mesa ya fue reasignada a un
  cliente nuevo. Esto protege el invariante de 003 RF-2 (una mesa
  ocupada tiene siempre un único pedido activo): el sistema deberá
  rechazar la anulación en ese caso, dejando el cobro original como
  está.
- Si la mesa no tiene otro pedido activo (sigue "pagada", o quedó
  "libre" sin que nadie la haya vuelto a ocupar todavía), el sistema sí
  deberá permitir anular el cobro. Al hacerlo deberá: dejar intacto el
  registro original del cobro (nunca lo edita ni lo borra), guardar
  quién anuló, cuándo, y el motivo; devolver el pedido a "en
  preparación" (`Order.Status.IN_PROGRESS`), quedando otra vez editable
  con normalidad (adiciones, anulaciones de ítem, 003); y devolver la
  mesa a "ocupada" si no lo estaba ya.
- Después de anular un cobro con éxito, el sistema deberá permitir
  volver a cobrar el mismo pedido con normalidad (RF-1 a RF-5), las
  veces que haga falta.

### RF-7 — Historial de cobros por pedido

- El sistema deberá permitir que un pedido acumule más de un registro
  de cobro a lo largo del tiempo (cero o más anulados, como mucho uno
  activo a la vez).
- El sistema deberá considerar que un pedido está "cobrado" si y solo
  si tiene exactamente un cobro activo asociado.

### RF-8 — Permisos y autenticación

- El sistema deberá exigir siempre una sesión autenticada válida para
  cobrar, anular un cobro, y crear o eliminar cuentas del catálogo.
- Cobrar, anular un cobro, y administrar el catálogo de opciones de
  pago deberán ser acciones exclusivas del rol admin (constitución,
  regla 5) — ningún mesero deberá poder acceder a ninguna de ellas.

## Casos límite

- El admin intenta cobrar un pedido que todavía está en "borrador" →
  el sistema rechaza la acción (RF-1).
- El admin intenta cobrar un pedido ya "cobrado" o "anulado" → el
  sistema rechaza la acción (RF-1).
- Dos admins envían el cobro del mismo pedido casi al mismo tiempo →
  solo el primero se registra; el segundo recibe un error de que el
  pedido ya está cobrado (RF-1).
- El admin intenta eliminar "Efectivo" del catálogo → el sistema lo
  rechaza siempre (RF-2).
- El admin intenta crear una cuenta con un nombre ya usado por otra →
  el sistema rechaza la creación (RF-2).
- El admin intenta eliminar una cuenta que ya usó al menos un cobro
  (incluso uno ya anulado) → el sistema rechaza la eliminación (RF-2).
- El admin intenta anular un cobro que ya está anulado → el sistema
  rechaza la acción (RF-6).
- El admin anula un cobro, pero el mesero ya había liberado la mesa
  antes de esa anulación, y nadie la ha vuelto a ocupar → la anulación
  procede: el pedido vuelve a "en preparación" y la mesa vuelve a
  "ocupada" (RF-6).
- El admin intenta anular un cobro, pero la mesa ya tiene un pedido
  nuevo activo (fue reasignada a otro cliente) → el sistema rechaza la
  anulación por completo, para no terminar con dos pedidos activos en
  la misma mesa (RF-6).
- Un pedido se cobra, se anula ese cobro, y se vuelve a cobrar varias
  veces seguidas → el sistema conserva cada registro de cobro anulado
  sin modificarlo, y el pedido solo refleja "cobrado" mientras tenga el
  cobro activo más reciente (RF-6, RF-7).
- Se agrega una adición o se anula un ítem después de que un cobro se
  anuló y el pedido volvió a "en preparación" → el pedido admite esos
  cambios con normalidad (003), y el siguiente cobro usará el total
  actualizado (RF-4).

## Fuera de alcance

- Los reportes y el cierre de caja diario (módulo de reportes, a
  especificar por separado).
- La creación, edición de pedidos, adiciones y anulaciones de ítems —
  ya cubierta por 003-mesas-pedidos. Este módulo solo reacciona al
  pedido ya armado y, al anular un cobro, delega de vuelta a esas
  mismas reglas de 003.
- La impresión de tickets de cocina (004-impresion-cocina) — no tiene
  relación con el cobro.
- Los pagos parciales o divididos entre varias opciones de pago en un
  mismo cobro — cada cobro se paga por completo con una sola opción
  del catálogo.
- Editar el nombre de una cuenta ya creada (RF-2) — solo se puede
  eliminar (si nunca se usó) y crear una nueva.
- Un límite de cuántas veces se puede anular y volver a cobrar un mismo
  pedido (RF-6, RF-7) — no existe tal límite en esta versión.
- Una vía alterna para corregir un cobro cuya mesa ya fue reasignada
  (RF-6) — en esta versión esa anulación queda bloqueada sin solución
  dentro del sistema; es una limitación conocida y aceptada.

## Criterios de finalización

- El admin puede cobrar un pedido en preparación cuya mesa está
  ocupada, eligiendo "Efectivo" o una cuenta del catálogo, viendo antes
  el total correcto (ítems activos, sin los anulados).
- Al confirmar, el pedido pasa a "cobrado", la mesa a "pagada" (sin
  liberarse), y queda guardado de forma permanente qué opción de pago
  se usó, el monto exacto, qué admin lo procesó y cuándo.
- Dos intentos de cobro casi simultáneos sobre el mismo pedido nunca
  producen dos cobros activos: el segundo siempre se rechaza.
- El admin puede crear cuentas nuevas en el catálogo (con nombres
  únicos y no vacíos) y eliminar únicamente las que ningún cobro haya
  usado nunca; "Efectivo" nunca se puede eliminar ni recrear; ningún
  nombre de cuenta se puede editar.
- El admin puede anular cualquier cobro activo (propio o de otro
  admin) con un motivo obligatorio, siempre que la mesa del pedido no
  tenga ya otro pedido activo; el cobro original queda intacto y
  visible, el pedido vuelve a "en preparación", y la mesa vuelve a
  "ocupada" si hacía falta.
- Un pedido puede volver a cobrarse tras anular un cobro anterior, y
  el sistema conserva el historial completo de todos los cobros
  (activos y anulados) que tuvo.
- Ningún endpoint de este módulo funciona sin sesión autenticada, y
  todos exigen rol admin.

## Dudas abiertas

Ninguna pendiente. De la ronda inicial de preguntas, quedaron resueltas
y ya incorporadas al texto:

- La corrección de un cobro erróneo es por anulación (nunca por edición
  ni borrado): el cobro original queda intacto, el pedido vuelve a "en
  preparación" y se puede volver a cobrar desde cero (RF-6).
- No hay un campo separado de "método de pago" y "cuenta": es una sola
  lista de opciones ("Efectivo" + cuentas creadas por el admin), sin
  distinguir tarjeta de transferencia (RF-2).
- Una cuenta se elimina solo si ningún cobro la usó nunca (ni uno
  anulado); su nombre es fijo una vez creada (RF-2).
- Cualquier admin puede anular cualquier cobro, no solo quien lo
  registró (RF-6).
- El monto de cada cobro se guarda como un valor fijo en el momento de
  confirmar, no se recalcula después (RF-3).
- Anular un cobro exige un motivo de texto obligatorio (RF-6).
- La vista de cobro no necesita un desglose en 3 grupos — basta el
  total ya calculado por 003 (RF-4).

De la revisión de QA posterior, quedaron resueltas y ya incorporadas:

- Si al anular un cobro la mesa ya tiene otro pedido activo (fue
  reasignada), la anulación se bloquea por completo, para proteger el
  invariante de 003 (una mesa, un único pedido activo); si la mesa
  sigue "pagada" o quedó "libre" sin reasignar, la anulación procede
  normalmente (RF-6).
- Los nombres de cuenta del catálogo deben ser únicos; el sistema
  rechaza crear una cuenta con un nombre ya usado (RF-2).
- Dos intentos de cobro casi simultáneos sobre el mismo pedido: el
  sistema rechaza el segundo en vez de duplicar el cobro o hacer un
  no-op silencioso (RF-1).
- Las reglas 4 y 5 de `docs/constitution.md` se ampliaron explícitamente
  para nombrar "anular un cobro" y "gestionar el catálogo de cuentas de
  pago" como acciones de admin con trazabilidad obligatoria.
