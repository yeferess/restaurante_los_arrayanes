# Especificación: Mesas y pedidos

## Contexto y objetivo

El mesero arma y gestiona los pedidos del restaurante desde su celular,
mesa por mesa: crea el pedido, agrega productos del menú (o ítems fuera
de carta con precio manual) con notas, lo envía, sigue agregando cosas
mientras el grupo está sentado, corrige sus propios errores (ítems mal
agregados, mesa equivocada) y marca cuándo fue entregado. El admin cobra
la mesa cuando el cliente paga en caja, y cualquier mesero libera la mesa
una vez cobrada para que vuelva a estar disponible. Este módulo depende
de [`001-autenticacion-usuarios`](../001-autenticacion-usuarios/spec.md)
(sesión y roles) y de
[`002-gestion-menu`](../002-gestion-menu/spec.md) (catálogo del que se
arman los pedidos), y respeta las reglas 4 y 5 de
[`docs/constitution.md`](../../docs/constitution.md).

> Nota: la regla 5 de la constitución se amplió como parte de esta spec
> para permitir que el mesero anule ítems y corrija la mesa de sus
> propios pedidos (antes eran acciones exclusivas de admin), y para
> enumerar explícitamente el resto de acciones ya decididas (enviar
> pedido, marcar entregado, liberar cualquier mesa pagada, y que el admin
> gestione el número de mesas). La regla 4 también se ajustó para que el
> cobro solo exija quién/cuándo, sin motivo. Ver `docs/constitution.md`
> para el texto vigente. "Corrección de mesa" (esta spec) y "cambio de
> mesa" (la constitución) son el mismo concepto.

## Usuarios

- **Mesero**: crea pedidos en mesas libres; agrega productos del catálogo
  o ítems fuera de carta con notas; envía el pedido y le hace adiciones;
  anula ítems con motivo y corrige la mesa — ambas acciones solo sobre
  sus propios pedidos; marca/desmarca el indicador "Entregado"; libera
  cualquier mesa ya pagada, sin importar quién tomó el pedido.
- **Admin**: gestiona el número de mesas; cobra el pedido de una mesa
  ocupada; anula un pedido completo con motivo; además de todo lo ya
  cubierto por 001-autenticacion-usuarios y 002-gestion-menu (gestión de
  usuarios/menú).

## Historias de usuario

- Como admin, quiero ajustar el número total de mesas del restaurante,
  para reflejar cambios en la distribución del salón sin tener que
  gestionar cada mesa una por una.
- Como mesero, quiero crear un pedido para una mesa y agregar los
  productos que piden, para empezar a atenderlos sin usar papel.
- Como mesero, quiero agregar una nota a un producto del pedido (ej.
  "sin cebolla"), para que se prepare como lo pidió el cliente.
- Como mesero, quiero agregar un ítem fuera de la carta con un precio
  manual, para cobrar algo que no está en el menú sin dar de alta un
  producto nuevo.
- Como mesero, quiero seguir agregando productos a un pedido que ya
  envié, para no tener que crear un pedido nuevo cada vez que piden algo
  más.
- Como mesero, quiero anular un ítem de un pedido con un motivo, para
  corregir un error mío sin perder de vista qué pasó y por qué.
- Como mesero, quiero corregir la mesa de un pedido si me equivoqué al
  crearlo, para que quede en la mesa correcta sin recrearlo.
- Como mesero, quiero marcar (y desmarcar si me equivoco) un pedido como
  "entregado" con un botón rápido desde la lista de pedidos, para saber
  qué ya salió a la mesa.
- Como mesero, quiero poder liberar una mesa ya cobrada aunque no haya
  sido yo quien tomó el pedido, para que vuelva a estar disponible
  aunque el mesero original lo olvide.
- Como admin, quiero cobrar el pedido de una mesa ocupada en cualquier
  momento, sin depender de un paso previo de "por cobrar".
- Como admin, quiero anular un pedido completo cuando haga falta, para
  corregir errores mayores que van más allá de un ítem suelto.

## Requisitos funcionales

### RF-1 — Mesas (entidad base)

- El sistema deberá siempre representar cada mesa con un número entero
  positivo (1, 2, 3...) y uno de tres estados: libre, ocupada o pagada.
- El sistema deberá siempre exponer al admin un único campo de "número
  de mesas" (un entero); las mesas existen siempre como el rango 1..N,
  sin huecos ni numeración manual por mesa individual.
- Cuando el admin sube el número de mesas de N a un valor mayor M, el
  sistema deberá crear las mesas N+1..M, todas en estado libre.
- Cuando el admin baja el número de mesas de N a un valor menor M, el
  sistema deberá eliminar las mesas M+1..N (las de numeración más alta).
- Si alguna de las mesas que se eliminarían al bajar el número no está
  libre, entonces el sistema deberá rechazar el cambio completo (no
  elimina ninguna).
- El sistema deberá siempre exigir que el número de mesas sea como
  mínimo 1.

### RF-2 — Creación de pedidos

- Cuando un mesero crea un pedido para una mesa libre, el sistema deberá
  crear el pedido en estado "borrador", asociado a ese mesero, y cambiar
  la mesa a "ocupada".
- Si un mesero intenta crear un pedido sobre una mesa que no está libre
  (ocupada o pagada), entonces el sistema deberá rechazar la creación.
- El sistema deberá siempre garantizar que una mesa ocupada tenga un
  único pedido activo (en "borrador" o "en preparación") en un momento
  dado; "el pedido de una mesa ocupada" (RF-9) se refiere siempre, sin
  ambigüedad, a ese único pedido activo.
- Mientras un pedido está en "borrador", el sistema deberá siempre
  permitir agregar ítems, y quitar un ítem ya agregado eliminando esa
  línea por completo, sin exigir motivo ni dejar rastro — distinto de
  anular un ítem ya enviado (ver RF-6).

### RF-3 — Ítems del pedido: productos del catálogo y fuera de carta

- Cuando un mesero agrega un producto del catálogo a un pedido, el
  sistema deberá crear una línea con el nombre y el precio vigentes del
  producto en ese momento, copiados (no referenciados en vivo — mismo
  patrón de congelamiento que define
  [002-gestion-menu RF-3/RF-5](../002-gestion-menu/spec.md)).
- Cuando un mesero agrega un ítem fuera de la carta, el sistema deberá
  exigir un nombre y un precio manual mayor que cero, y crear la línea
  con esos datos.
- El sistema deberá siempre exigir que el nombre de un ítem fuera de
  carta no esté vacío y tenga como máximo 100 caracteres.
- El sistema deberá siempre permitir nombres repetidos entre ítems fuera
  de carta, sin exigir unicidad (a diferencia del nombre de un producto
  del catálogo en 002-gestion-menu).
- Un producto del catálogo marcado como no disponible no aparece en la
  lectura de menú del mesero (002-gestion-menu RF-7), por lo que el
  sistema nunca lo ofrece como opción para agregar a un pedido.
- Si un producto del catálogo deja de estar disponible entre que el
  mesero lo vio en su menú y el momento en que intenta agregarlo,
  entonces el sistema deberá rechazar la operación: el backend siempre
  revalida la disponibilidad del producto al agregarlo, sin confiar
  únicamente en el estado del menú ya cargado en el frontend.

### RF-4 — Notas por ítem

- Cuando un mesero agrega una nota a un ítem del pedido (de catálogo o
  fuera de carta), el sistema deberá guardarla asociada a esa línea
  específica, no al pedido completo.
- El sistema deberá siempre permitir agregar un ítem sin nota (es
  opcional).
- El sistema deberá siempre exigir que una nota no supere los 200
  caracteres, sin ninguna otra restricción de formato.
- El sistema deberá siempre permitir editar el texto de una nota ya
  guardada mientras su ítem no esté anulado y el pedido no esté cobrado
  ni anulado.

### RF-5 — Envío del pedido y adiciones

- Cuando un mesero envía un pedido en "borrador", el sistema deberá
  cambiar su estado a "en preparación".
- Si el pedido no tiene ningún ítem, entonces el sistema deberá rechazar
  el envío.
- Si un mesero intenta enviar un pedido que ya no está en "borrador"
  (ya está "en preparación", "cobrado" o "anulado"), entonces el sistema
  deberá ignorar la solicitud sin efecto y sin error.
- Cuando un mesero agrega un ítem a un pedido que ya está "en
  preparación", el sistema deberá registrarlo como una adición, aplicando
  las mismas reglas de RF-3 y RF-4.
- Si el pedido ya está "cobrado" o "anulado", entonces el sistema deberá
  rechazar cualquier adición de ítems.
- La transición real de "borrador" a "en preparación" (no un reenvío sin
  efecto) es también el momento en que el sistema asigna el número del
  día del pedido (RF-14).

### RF-6 — Anulación de ítems

- Cuando un mesero anula un ítem de uno de sus propios pedidos ya "en
  preparación", el sistema deberá exigir un motivo y marcar el ítem como
  anulado sin eliminarlo del historial del pedido (distinto de quitar un
  ítem en "borrador", ver RF-2).
- El sistema deberá siempre excluir los ítems anulados del total del
  pedido.
- Si un mesero intenta anular un ítem de un pedido que no es suyo,
  entonces el sistema deberá rechazar la acción.
- Si el pedido ya está "cobrado" o "anulado", entonces el sistema deberá
  rechazar la anulación de ítems.
- Cuando el último ítem activo de un pedido "en preparación" queda
  anulado, el sistema deberá anular automáticamente el pedido completo
  (RF-11) — reutilizando el mismo mesero, el mismo momento y el mismo
  motivo de esa anulación de ítem, sin exigir un motivo adicional — y
  liberar la mesa asociada de inmediato.

### RF-7 — Corrección de la mesa de un pedido

- Cuando un mesero corrige la mesa de uno de sus propios pedidos, el
  sistema deberá exigir que la mesa destino esté libre.
- Cuando la corrección se aplica, el sistema deberá cambiar la mesa
  original a "libre" y la mesa destino a "ocupada".
- Si la mesa destino no está libre, entonces el sistema deberá rechazar
  la corrección.
- Si un mesero intenta corregir la mesa de un pedido que no es suyo,
  entonces el sistema deberá rechazar la acción.
- El sistema deberá siempre considerar "propio" el pedido del mesero que
  lo creó (RF-2) de forma permanente: corregir la mesa (este RF) nunca
  transfiere la propiedad del pedido a otro mesero.
- Si el pedido ya está "cobrado" o "anulado", entonces el sistema deberá
  rechazar la corrección de mesa.

### RF-8 — Indicador "Entregado"

- El sistema deberá siempre tratar "entregado" como un indicador
  booleano independiente del estado principal del pedido, mientras ese
  estado sea "borrador", "en preparación" o "cobrado".
- Cuando un mesero marca o desmarca un pedido como entregado, el sistema
  deberá aplicar el cambio de inmediato, sin exigir motivo.
- Si el pedido está "anulado", entonces el sistema deberá rechazar
  marcar o desmarcar "entregado" (deja de ser relevante).
- El sistema deberá siempre ofrecer este control como una acción rápida
  (un botón) desde la lista de pedidos.
- El sistema deberá mostrar al mesero "Entregado" como etiqueta visible
  del pedido mientras su estado principal sea "en preparación" y esté
  marcado como entregado — en vez de "en preparación" —, sin que esto
  constituya un quinto estado del pedido: sigue siendo "en preparación"
  para todo efecto de negocio (adiciones, anulación de ítems,
  corrección de mesa, cobro — RF-5, RF-6, RF-7, RF-9 — siguen
  funcionando exactamente igual, sin exigir ni verse afectados por este
  indicador). En "borrador", "cobrado" o "anulado", la etiqueta visible
  no cambia por este indicador.

### RF-9 — Cobro del pedido

- Cuando un admin cobra el pedido de una mesa ocupada, el sistema deberá
  cambiar el estado del pedido a "cobrado" y el estado de la mesa a
  "pagada".
- El sistema deberá siempre permitir el cobro en cualquier momento
  mientras la mesa esté ocupada, sin exigir que el pedido esté marcado
  como entregado.
- Si un mesero intenta cobrar un pedido, entonces el sistema deberá
  rechazar la acción (acción exclusiva de admin).
- El sistema deberá mostrar en cada tarjeta del panel de pedidos
  entrantes del admin el mesero que tomó el pedido.
- Si la mesa no está ocupada (está libre o ya pagada), entonces el
  sistema deberá rechazar el cobro.

### RF-10 — Liberación de la mesa

- Cuando cualquier mesero autenticado libera una mesa "pagada", el
  sistema deberá cambiar su estado a "libre".
- El sistema deberá siempre permitir esta acción a cualquier mesero, sin
  importar quién tomó el pedido original.
- Si la mesa no está "pagada" (está libre u ocupada sin cobrar),
  entonces el sistema deberá rechazar la liberación.
- El sistema deberá siempre ofrecer esta acción como un botón rápido,
  igual de simple que "Entregado" (RF-8).

### RF-11 — Anulación del pedido completo

- Cuando un admin anula un pedido completo — ya sea que esté en
  "borrador" o "en preparación" —, el sistema deberá exigir un motivo y
  marcar el pedido como anulado.
- Si un mesero intenta anular un pedido completo, entonces el sistema
  deberá rechazar la acción (acción exclusiva de admin).
- Si el pedido ya está "cobrado", entonces el sistema deberá rechazar la
  anulación completa — igual de "congelado" que ante RF-5/RF-6. Un error
  de cobro (ej. se cobró la mesa equivocada) se resuelve de forma manual,
  fuera del sistema.
- Cuando un pedido completo se anula (lo cual solo puede pasar antes de
  cobrar, por el punto anterior), el sistema deberá volver la mesa
  asociada a "libre" de inmediato.

### RF-12 — Trazabilidad

- Cuando se anula un ítem (RF-6), se anula un pedido completo (RF-11,
  incluida la anulación automática por quedarse sin ítems activos), o se
  corrige la mesa de un pedido (RF-7), el sistema deberá siempre
  registrar quién ejecutó la acción, cuándo, y el motivo, antes de
  aplicarla (regla 4 de la constitución).
- Cuando se cobra un pedido (RF-9), el sistema deberá siempre registrar
  quién y cuándo — sin exigir un motivo escrito, ya que cobrar no es una
  acción que requiera justificación (regla 4 de la constitución,
  actualizada).
- El sistema deberá siempre rechazar cualquiera de estas acciones si no
  puede completar su registro de trazabilidad correspondiente.

### RF-13 — Permisos y autenticación

- El sistema deberá exigir siempre una sesión autenticada válida para
  cualquier endpoint de mesas o pedidos.
- El sistema deberá siempre permitir a un mesero ver el estado (libre/
  ocupada/pagada) de todas las mesas, pero solo gestionar el contenido
  (ítems, notas, adiciones, anulación de ítems, corrección de mesa) de
  los pedidos que él mismo creó.
- El sistema deberá siempre impedir que un mesero consulte el contenido
  (ítems, notas, total) de un pedido que no sea suyo; de un pedido ajeno
  solo ve el estado de la mesa asociada. El número del día (RF-14) no se
  considera parte de ese contenido restringido: cualquier mesero
  autenticado puede verlo junto al estado de la mesa, sea o no el dueño
  del pedido.
- El sistema deberá siempre restringir a admin las acciones de cobro
  (RF-9) y anulación de pedido completo (RF-11).
- El sistema deberá siempre permitir a cualquier mesero autenticado
  liberar una mesa pagada (RF-10), sin restricción de dueño.

### RF-14 — Número del día

- Además de su identificador interno (único global, creciente, inmutable
  — la llave que usan la base de datos, la API, y el futuro módulo de
  estadísticas), el sistema deberá asignar a cada pedido enviado un
  "número del día": un entero que se reinicia a 1 cada día a las 00:00
  hora local del restaurante (zona horaria `America/Bogota`), único
  entre los pedidos de ese mismo día, pero no entre días distintos.
- El sistema deberá asignar el número del día exactamente en el momento
  en que un pedido pasa de "borrador" a "en preparación" (RF-5) — nunca
  antes. Un pedido que se queda en "borrador" (incluido uno que nunca
  llega a enviarse) nunca consume un número del día.
- El sistema deberá garantizar que dos envíos casi simultáneos reciban
  siempre números del día distintos entre sí, sin importar en qué orden
  terminen de procesarse sus respectivas solicitudes. Lo único
  garantizado es que un número nunca se repite dentro del mismo día: si
  una asignación falla a mitad de proceso (por ejemplo, una caída del
  servidor), el número siguiente puede dejar un hueco en la secuencia de
  ese día (ej. 5, 6, 8), sin que el sistema intente rellenarlo después.
- Una vez asignado, el sistema deberá tratar el número del día de un
  pedido como inmutable: las adiciones (RF-5), las anulaciones de ítem o
  de pedido completo (RF-6, RF-11), y la corrección de mesa (RF-7) que
  ocurran después nunca generan ni consumen un número del día nuevo —
  siguen mostrando el mismo número que el pedido ya tenía desde que se
  envió. Si el pedido se anula por completo (RF-11), su número del día
  queda consumido de forma permanente: nunca se reutiliza en un pedido
  posterior enviado ese mismo día.
- El sistema deberá mostrar siempre el número del día con el formato
  "N° " seguido del entero simple, sin ceros a la izquierda (ej.
  "N° 7"), junto con la fecha y hora exactas en que el pedido fue
  enviado (RF-5), con menor jerarquía visual que el número. Esta regla
  aplica de forma general a cualquier pantalla donde se identifique un
  pedido ante mesero, admin o cocina; las que siguen son ejemplos de las
  pantallas que existen hoy, no una lista cerrada: la lista de pedidos
  del mesero, el panel de pedidos entrantes del admin, el detalle de un
  pedido, y el consolidado de cobro ([005-cobro](../005-cobro/spec.md)).
  Excepción: el ticket de cocina impreso
  ([004-impresion-cocina](../004-impresion-cocina/spec.md)) queda exento
  de la jerarquía visual — al imprimirse en texto plano de un solo
  estilo (004-RF-7), ahí el número y la fecha/hora se muestran con el
  mismo tamaño de letra.
- El sistema nunca deberá mostrar el identificador interno de un pedido
  como texto visible/renderizado (etiquetas, listas, detalle, ticket) en
  ninguna pantalla de mesero, admin o cocina — queda reservado para la
  base de datos, la API, y el futuro módulo de estadísticas, que siempre
  deberá usarlo como llave, nunca el número del día. Esta restricción no
  aplica a las rutas (URLs) ni a los payloads de la API REST del propio
  sistema, que sí pueden seguir usando el identificador interno como
  identificador de recurso (constitución, regla 3).
- Los pedidos ya enviados antes de desplegar este cambio no deberán
  tener un número del día asignado retroactivamente; la numeración
  empieza limpia desde el primer pedido que se envíe después del
  despliegue.

### RF-15 — Mesas retenidas por pedidos olvidados

- Si un pedido en "borrador" lleva más de 10 minutos desde su creación
  sin ningún ítem, o fue creado en un día anterior (hora local), tenga o
  no ítems, entonces el sistema deberá eliminarlo — igual que
  "Eliminar" en RF-2, sin motivo ni rastro — y volver su mesa a "libre".
  La limpieza ocurre de forma perezosa, la próxima vez que alguien lea
  las mesas, la lista de pedidos del mesero o las mesas ocupadas, o
  intente crear un pedido; nunca se elimina un borrador de hoy que tenga
  ítems, ni un pedido ya enviado. Así ningún borrador se guarda de un
  día para otro.
- Cuando el mesero sale de la pantalla de un pedido en "borrador" que no
  tiene ningún ítem, el sistema deberá eliminarlo de inmediato, sin
  esperar los 10 minutos.
- Mientras un pedido en "borrador" con ítems lleve más de 15 minutos sin
  enviarse, el sistema deberá mostrarle a su mesero, en su lista de
  pedidos, el aviso "Borrador sin enviar: envíalo o elimínalo para
  liberar la mesa".
- El sistema deberá permitir al admin ver cada mesa ocupada junto con el
  pedido que la retiene (estado "borrador" o "en preparación", mesero,
  desde cuándo, cantidad de ítems y total), y anular ese pedido desde
  ahí con el mismo flujo de RF-11 (motivo obligatorio y trazabilidad de
  RF-12).
- Cuando el pedido que retiene la mesa está en "borrador" — que el admin
  no ve en los pedidos entrantes —, el sistema deberá ofrecerle
  "Eliminar borrador": con solo confirmar, el pedido queda anulado y la
  mesa vuelve a "libre". Sigue siendo una anulación de pedido completo
  (RF-11) con trazabilidad (RF-12, regla 4): el sistema registra quién y
  cuándo, con el motivo fijo "Borrador eliminado por el admin", sin
  pedirle que lo escriba. Un pedido ya enviado no admite esta acción.
- Si una mesa lleva más de 3 horas ocupada por el mismo pedido, el
  sistema deberá destacarla en esa vista y mostrar en el panel de
  pedidos entrantes del admin el aviso "Hay N mesas ocupadas desde hace
  más de 3 horas", con un enlace a la gestión de mesas.

### RF-16 — "Mis pedidos" por día

- Cuando un mesero abre "Mis pedidos", el sistema deberá mostrarle los
  pedidos que creó hoy (hora local), más los de días anteriores que
  siguen pendientes: los que están "en preparación" y el pedido cobrado
  de una mesa que sigue "pagada" (para poder liberarla, RF-10).
- El sistema deberá permitirle elegir otra fecha (nunca futura) y, en
  ese caso, mostrar solo los pedidos que creó ese día, en cualquier
  estado.
- Si la fecha no tiene el formato AAAA-MM-DD, el sistema deberá rechazar
  la consulta.

## Requisitos no funcionales

- El sistema deberá operar completamente dentro de la red WiFi local del
  restaurante; crear, enviar, anular, cobrar, liberar y corregir la mesa
  de un pedido no deben depender de internet (constitución, regla 2).
- El sistema deberá almacenar los precios de las líneas de pedido con
  precisión monetaria suficiente para evitar errores de redondeo en el
  cobro (mismo criterio que 002-gestion-menu).
- Ante dos solicitudes casi simultáneas que dependan del mismo estado de
  mesa (crear pedido, cobrar, liberar, corregir mesa, o cambiar el número
  de mesas), el sistema deberá siempre procesar la primera que le llegue
  y rechazar la segunda por precondición de estado ya no cumplida (mismo
  rechazo ya definido para ese caso en cada RF), sin necesitar un
  mecanismo de bloqueo adicional.
- Ante dos envíos casi simultáneos de pedidos distintos (RF-14), el
  sistema deberá garantizar que ambos reciban número del día — nunca
  rechazar uno de los dos por esta causa; a diferencia del punto
  anterior, aquí ambas solicitudes tienen éxito, solo se asegura que su
  número del día nunca se repita (no que sean estrictamente
  consecutivos, ver RF-14).

## Casos límite

- Mesero intenta crear un pedido en una mesa ocupada o pagada → RF-2
  (rechazado).
- Se intenta enviar un pedido sin ningún ítem → RF-5 (rechazado).
- Se intenta agregar un ítem o anular uno en un pedido ya cobrado → RF-5,
  RF-6 (rechazado).
- Se intenta corregir la mesa de un pedido ya cobrado → RF-7 (rechazado).
- Mesero intenta anular un ítem o corregir la mesa de un pedido que no es
  suyo → RF-6, RF-7 (rechazado).
- Se intenta corregir la mesa de un pedido hacia una mesa que no está
  libre → RF-7 (rechazado).
- Mesero intenta cobrar un pedido, o admin no está involucrado → RF-9
  (rechazado, acción exclusiva de admin).
- Se intenta liberar una mesa libre u ocupada sin cobrar → RF-10
  (rechazado).
- Un mesero distinto al que tomó el pedido libera la mesa ya pagada →
  RF-10 (permitido explícitamente).
- Se intenta agregar un ítem fuera de carta con nombre vacío/largo o
  precio ≤0 → RF-3 (rechazado).
- Se intenta agregar una nota que supera el máximo de caracteres → RF-4
  (rechazado).
- Se marca/desmarca "Entregado" repetidamente, en cualquier estado del
  pedido → RF-8 (siempre permitido, sin motivo).
- Un pedido "en preparación" marcado como entregado (etiqueta visible
  "Entregado") se cobra → RF-8, RF-9 (la etiqueta visible pasa a
  "Cobrado"; el indicador "entregado" no se pierde, solo deja de
  mostrarse mientras el pedido esté cobrado).
- Se anula un cobro de un pedido que seguía marcado como entregado
  (005-cobro RF-6) → RF-8 (el pedido vuelve a "en preparación" y su
  etiqueta visible vuelve a mostrar "Entregado", porque el indicador
  nunca se modificó).
- El admin sube el número de mesas → RF-1 (se crean las mesas nuevas,
  todas libres).
- El admin baja el número de mesas y alguna de las que se eliminarían no
  está libre → RF-1 (rechazado, no se elimina ninguna).
- Se intenta anular un pedido completo ya cobrado → RF-11 (rechazado; el
  error se corrige manualmente, fuera del sistema).
- Se intenta reenviar un pedido que ya no está en "borrador" → RF-5
  (ignorado, sin efecto ni error).
- Se anula el último ítem activo de un pedido "en preparación" → RF-6/
  RF-11 (el pedido completo se anula automáticamente, reutilizando el
  mismo mesero/motivo, y la mesa vuelve a libre).
- Se corrige la mesa de un pedido eligiendo la misma mesa en la que ya
  está → RF-7 (rechazado: esa mesa está "ocupada" por ese mismo pedido,
  nunca "libre").
- Se intenta agregar/anular ítems, corregir la mesa, o marcar/desmarcar
  "Entregado" en un pedido "anulado" → RF-5, RF-6, RF-7, RF-8 (todos
  rechazados, igual que un pedido "cobrado").
- El admin intenta bajar el número de mesas por debajo de 1 → RF-1
  (rechazado).
- Dos meseros crean un pedido en la misma mesa libre casi al mismo
  tiempo → RF-2 (gana el primero; el segundo se rechaza porque la mesa
  ya no está libre).
- Dos admins cobran la misma mesa casi al mismo tiempo → RF-9 (gana el
  primero; el segundo se rechaza porque la mesa ya no está ocupada).
- Dos meseros liberan la misma mesa casi al mismo tiempo → RF-10 (gana
  el primero; el segundo se rechaza porque la mesa ya no está pagada).
- El admin baja el número de mesas justo cuando un mesero crea un pedido
  en una de las mesas que se eliminarían → RF-1/RF-2 (gana la primera
  solicitud procesada; la otra se rechaza por el estado ya cambiado).
- Un producto del catálogo se elimina (002-gestion-menu RF-5) después de
  haberse agregado a un pedido activo → sin efecto: la línea del pedido
  ya conserva su propia copia de nombre y precio (RF-3).
- Un pedido se envía a las 23:59:59 hora local y otro un minuto después
  (00:00:00 del día siguiente) → RF-14 (el primero conserva el último
  número de su día; el segundo arranca en 1, aunque entre ambos solo
  haya pasado un minuto real).
- Dos meseros envían su pedido casi al mismo tiempo → RF-14 (ambos
  reciben número del día, siempre distintos entre sí; nunca se repiten,
  aunque un fallo a mitad de proceso pueda dejar un hueco en la
  secuencia).
- Se agrega una adición, o se anula un ítem o el pedido completo, sobre
  un pedido ya enviado → RF-14 (sigue mostrando el mismo número del día
  que ya tenía; nunca genera uno nuevo).
- Un pedido se queda en "borrador" y nunca se envía → RF-14 (nunca llega
  a tener número del día) y RF-15 (si no tiene ítems se elimina solo a
  los 10 minutos; si tiene ítems, su mesero ve un aviso a los 15 minutos,
  el admin puede eliminarlo con un clic desde la gestión de mesas, y en
  cualquier caso desaparece al día siguiente).
- Un pedido se envía antes de medianoche y sigue "en preparación" al día
  siguiente → RF-16 (sigue apareciendo en "Mis pedidos" de hoy hasta que
  se cobra o se anula).
- Una mesa se cobra antes de medianoche y nadie la libera → RF-16 (su
  pedido sigue en "Mis pedidos" de hoy, con "Liberar mesa", hasta que se
  libera).
- Un mesero toca una mesa por error y sale sin agregar nada → RF-15 (el
  borrador vacío se elimina al salir de la pantalla del pedido, o a los
  10 minutos si la salida no se detecta, por ejemplo al bloquear el
  teléfono).
- Un pedido enviado nunca se cobra ni se anula → RF-15 (a las 3 horas el
  admin ve el aviso de mesa ocupada y la anula con motivo, o la cobra).
- Un pedido ya estaba enviado antes de desplegar el número del día → RF-14
  (no se le asigna uno retroactivamente; queda sin número de forma
  permanente).
- Un pedido se envía antes de medianoche y sigue "en preparación" cuando
  cruza la medianoche hora local, recibiendo una adición o anulación ya
  en el día siguiente → RF-14 (sigue mostrando el número y la fecha/hora
  de envío del día anterior; no adopta un número del nuevo día).
- Por el caso anterior, un pedido de ayer que sigue activo pasada la
  medianoche puede coincidir en número con un pedido de hoy (ej. ambos
  "N° 1") mientras ambos están visibles a la vez en una misma lista →
  RF-14 (se distinguen únicamente por la fecha/hora que acompaña al
  número, nunca por el número solo).
- Se corrige la mesa (RF-7) de un pedido que ya tiene número del día
  asignado → RF-14 (el número y su fecha/hora de envío no cambian).
- Se anula por completo un pedido que ya tenía número del día asignado
  → RF-14 (ese número queda consumido de forma permanente para ese día;
  el siguiente pedido enviado recibe el que sigue en la secuencia, nunca
  el del pedido anulado).

## Fuera de alcance

- Registrar el método de pago (efectivo, tarjeta, etc.), pagos divididos
  entre varios métodos (ej. "una parte en efectivo y otra por Nequi"), o
  cualquier otra nota/detalle de facturación o caja — en este módulo
  "cobrar" es solo el evento que cambia el estado del pedido y de la mesa
  (RF-9), sin datos de cómo se pagó. Eso pertenece al futuro módulo de
  pagos.
- El formato o la impresión del ticket/comanda.
- La gestión del catálogo de productos (categorías, precios,
  disponibilidad) — ya cubierta por 002-gestion-menu.
- La unión física de varias mesas para grupos grandes — es un tema
  operativo del restaurante, no algo que el software deba modelar.
- Múltiples pedidos simultáneos activos sobre una misma mesa (ej. cuentas
  separadas por comensal) — mientras una mesa está ocupada existe un
  único pedido activo.
- Reasignar un pedido existente a un mesero distinto del que lo creó (por
  cambio de turno, por ejemplo) — solo RF-10 (liberar mesa) está
  explícitamente abierto a cualquier mesero; todo lo demás queda
  restringido al mesero original. Queda como limitación conocida de esta
  versión, a resolver en una futura iteración si hace falta.
- Editar el número de una mesa individual o mantener huecos en la
  numeración — las mesas son siempre el rango 1..N (RF-1); no hay
  identificadores personalizados ni eliminación de una mesa específica
  fuera de la más alta.
- Una vista en tiempo real tipo dashboard para el admin sobre todas las
  mesas/pedidos, más allá de la lista de mesas ocupadas de RF-15 — no fue
  solicitada para este módulo (a diferencia de la
  propagación en tiempo real del menú en 002-gestion-menu).
- Mostrar o usar el identificador interno del pedido en cualquier
  pantalla de mesero, admin o cocina (RF-14) — nunca se muestra; solo
  existe en la base de datos, la API y el futuro módulo de estadísticas.
- Asignar número del día retroactivamente a pedidos ya enviados antes de
  este cambio (RF-14) — quedan sin número, de forma permanente.
- El futuro módulo de estadísticas en sí (qué reportes existen, cómo se
  calculan) — aquí solo se fija que, cuando exista, deberá usar siempre
  el identificador interno como llave (RF-14).

## Criterios de finalización

- Un admin puede subir o bajar el número total de mesas; al subirlo se
  crean mesas nuevas libres, al bajarlo se elimina desde la numeración
  más alta, y se rechaza si alguna de las que se eliminarían no está
  libre.
- Un mesero puede crear un pedido en una mesa libre (y no en una que no
  lo esté), agregar productos del catálogo y/o ítems fuera de carta con
  precio manual, y agregarles una nota opcional.
- Un mesero puede enviar un pedido con al menos un ítem, y seguir
  agregándole ítems después (adiciones) mientras no esté cobrado.
- Un mesero puede anular un ítem de sus propios pedidos con motivo (y no
  de los de otro mesero), excluyéndolo del total; no puede hacerlo si el
  pedido ya está cobrado.
- Un mesero puede corregir la mesa de sus propios pedidos únicamente
  hacia una mesa libre; no puede hacerlo sobre pedidos ajenos ni sobre
  pedidos ya cobrados.
- Un mesero puede marcar y desmarcar libremente el indicador "Entregado"
  desde la lista de pedidos, en cualquier estado del pedido; mientras el
  pedido esté "en preparación", la etiqueta visible pasa a mostrar
  "Entregado" en vez de "en preparación".
- Solo un admin puede cobrar un pedido (mesa ocupada → pagada) y anular
  un pedido completo con motivo; un mesero no puede hacer ninguna de las
  dos cosas.
- Cualquier mesero puede liberar una mesa pagada (pagada → libre), sin
  importar quién tomó el pedido; no puede liberar una mesa libre u
  ocupada sin cobrar.
- Cobro, anulación de ítem, anulación de pedido completo y corrección de
  mesa quedan registrados con quién y cuándo (y motivo, donde aplique).
- Un pedido que se queda sin ningún ítem activo mientras está "en
  preparación" se anula automáticamente por completo, liberando la mesa.
- Un pedido "anulado" no admite adiciones, anulación de ítems,
  corrección de mesa, ni marcar/desmarcar "Entregado".
- Un mesero no puede ver el contenido de un pedido que no sea suyo, solo
  el estado de la mesa asociada.
- Ningún endpoint de mesas o pedidos funciona sin sesión autenticada.
- Cada pedido enviado recibe un número del día único dentro de su día
  (reiniciando a 1 cada medianoche, hora de Bogotá), que no cambia con
  adiciones ni anulaciones posteriores; el identificador interno nunca
  aparece en pantalla, solo el número del día junto con la fecha/hora de
  envío.

## Dudas abiertas

Ninguna pendiente. De la ronda inicial de dudas, quedaron resueltas y ya
incorporadas al texto:

- La nota de un ítem tiene un máximo de 200 caracteres, texto libre sin
  más restricción de formato, y se puede editar mientras el ítem y el
  pedido sigan activos (RF-4).
- Un pedido ya cobrado nunca puede anularse por completo (RF-11); un
  cobro equivocado se corrige manualmente, fuera del sistema. Por eso la
  mesa siempre vuelve a "libre" al anular (solo puede pasar antes de
  cobrar).
- El cobro (RF-9) solo registra quién y cuándo, sin motivo — se ajustó la
  regla 4 de la constitución para reflejarlo (anulación y cambio de mesa
  sí siguen exigiendo motivo).
- Las mesas se gestionan con un único campo "número de mesas" (RF-1, con
  mínimo 1): no hay identificadores personalizados, edición individual,
  ni huecos en la numeración.
- La reasignación de un pedido a otro mesero por cambio de turno queda
  fuera de alcance de esta versión (ver "Fuera de alcance").

De la revisión de QA posterior, quedaron resueltas y ya incorporadas:

- El backend siempre revalida disponibilidad de un producto al
  agregarlo, sin confiar solo en el frontend (RF-3).
- El nombre de un ítem fuera de carta no exige unicidad (RF-3).
- "Pedido propio" es siempre el mesero que lo creó, de forma permanente;
  corregir la mesa no transfiere la propiedad (RF-7).
- "Quitar" un ítem en borrador (sin motivo, se borra la línea) y "anular"
  un ítem ya en preparación (con motivo, queda marcado) son dos mecánicas
  distintas (RF-2, RF-6).
- Un pedido "anulado" es un cuarto estado, además de borrador/en
  preparación/cobrado, y queda tan congelado como uno cobrado frente a
  adiciones, anulación de ítems, corrección de mesa y "Entregado" (RF-5,
  RF-6, RF-7, RF-8).
- Si el último ítem activo de un pedido "en preparación" se anula, el
  pedido completo se anula automáticamente, reutilizando el mismo
  mesero/motivo (RF-6, RF-11).
- Reenviar un pedido que ya no está en "borrador" no hace nada (RF-5).
- Un mesero no ve el contenido de pedidos ajenos, solo el estado de la
  mesa (RF-13).
- La concurrencia entre solicitudes que dependen del mismo estado de
  mesa se resuelve con "gana la primera, la segunda se rechaza por
  precondición" (Requisitos no funcionales).

De la ronda de "número del día" (nuevo requisito posterior), quedaron
resueltas y ya incorporadas:

- Las adiciones y las anulaciones (de ítem o de pedido completo) sobre
  un pedido ya enviado nunca generan un número del día nuevo; siempre
  muestran el que el pedido ya tenía (RF-14).
- Los pedidos ya enviados antes de este cambio se quedan sin número del
  día; no hay migración retroactiva (RF-14).
- El identificador interno deja de mostrarse en toda la interfaz; solo
  se usa internamente y en el futuro módulo de estadísticas (RF-14).
- La zona horaria para calcular el reinicio diario es `America/Bogota`
  (RF-14).

De la auditoría QA posterior sobre el "número del día", quedaron
resueltas y ya incorporadas:

- El ticket de cocina impreso queda exento de la jerarquía visual entre
  número y fecha/hora: se imprime con el mismo tamaño de letra para
  ambos, al ser texto plano de un solo estilo (RF-14, 004-RF-7).
- La lista de pantallas de RF-14 es ilustrativa, no exhaustiva: la regla
  de usar el número del día (nunca el identificador interno) aplica a
  cualquier pantalla donde se identifique un pedido ante mesero, admin o
  cocina, incluidas las que se creen a futuro (RF-14).
- El número del día se muestra con el formato "N° " seguido del entero
  simple, sin ceros a la izquierda (ej. "N° 7") (RF-14).
- La garantía de "distintos" no exige una secuencia sin huecos: un fallo
  a mitad de la asignación puede dejar un hueco en la numeración de ese
  día, sin que el sistema intente rellenarlo (RF-14).

De la segunda ronda de QA (contradicciones y casos límite sobre el
"número del día"), quedaron resueltas y ya incorporadas:

- La prohibición de mostrar el identificador interno aplica solo a
  texto visible/renderizado; no restringe las URLs ni los payloads de
  la propia API REST, que siguen usándolo como identificador de recurso
  (RF-14).
- El número del día de un pedido ajeno sí es visible para cualquier
  mesero autenticado (no se considera "contenido" restringido por
  RF-13); solo el resto del contenido del pedido sigue vedado al que no
  es su dueño (RF-13, RF-14).
- El número del día de un pedido anulado nunca se reutiliza: queda
  consumido de forma permanente para ese día (RF-14).
- Asignar el número del día no se registra como una acción trazable
  aparte (RF-12): es un efecto automático del envío del pedido (RF-5),
  que ya registra quién y cuándo lo envió.

De la ronda sobre la etiqueta visible de "Entregado" (RF-8), quedó
resuelto y ya incorporado:

- "Entregado" sigue siendo un indicador booleano independiente a nivel
  de negocio (no gatilla ni bloquea ninguna otra acción); lo único
  nuevo es que, mientras el pedido esté "en preparación", su etiqueta
  visible pasa a mostrar "Entregado" en vez de "en preparación" — no se
  agrega un quinto estado real del pedido (RF-8).
