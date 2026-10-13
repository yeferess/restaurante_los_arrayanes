# 002 · Gestión del menú (catálogo de productos)

## Contexto y objetivo

El admin gestiona el catálogo de productos del restaurante (nombre,
categoría, precio, disponibilidad) desde el panel `/admin`. El mesero solo
lo consulta, nunca lo modifica. Los cambios deben verse reflejados en
tiempo real en las apps de los meseros, con un botón manual de respaldo
por si el evento en tiempo real no llega. Este módulo depende de
[`001-autenticacion-usuarios`](../001-autenticacion-usuarios/spec.md): todo
endpoint de menú exige sesión autenticada y valida el rol, en línea con la
regla 5 de [`docs/constitution.md`](../../docs/constitution.md).

## Usuarios

- **Admin**: crea, renombra y elimina categorías, y crea, edita, marca
  como disponible/no disponible y elimina productos del menú desde
  `/admin`.
- **Mesero**: consulta el menú vigente (productos y sus categorías) desde
  su PWA; no puede crear, editar ni eliminar nada del catálogo.

## Historias de usuario

- Como admin, quiero crear y renombrar categorías del menú, para organizar
  los productos de forma consistente sin depender de que yo mismo escriba
  el mismo texto igual cada vez.
- Como admin, quiero eliminar una categoría que ya no uso y no tiene
  productos asignados, para mantener la lista de categorías limpia.
- Como admin, quiero crear un producto nuevo con nombre, categoría, precio
  y disponibilidad, para que los meseros puedan empezar a ofrecerlo de
  inmediato.
- Como admin, quiero editar el precio o la categoría de un producto
  existente, para corregir errores o actualizar el menú sin tener que
  recrearlo.
- Como admin, quiero marcar un producto como no disponible sin afectar los
  pedidos que ya lo incluyen, para reflejar que hoy no hay stock sin
  interferir con las mesas ya en curso.
- Como admin, quiero poder eliminar definitivamente cualquier producto que
  ya no necesito en el catálogo, sin importar si tuvo pedidos en el
  pasado, para no acumular basura ni tener que mantener productos que ya
  no ofrezco.
- Como mesero, quiero ver el menú actualizado en mi PWA sin tener que hacer
  nada, para no ofrecer productos que ya no están disponibles.
- Como mesero, quiero un botón para forzar la actualización del menú, para
  no quedar con datos viejos si la notificación en tiempo real falla.

## Requisitos funcionales

### RF-1 — Gestión de categorías

- Cuando un admin crea una categoría con un nombre, el sistema deberá
  guardarla en el catálogo de categorías.
- El sistema deberá siempre exigir que el nombre de la categoría no esté
  vacío y tenga como máximo 50 caracteres.
- Si el nombre de la categoría ya existe (ignorando mayúsculas y
  minúsculas), entonces el sistema deberá rechazar la creación o el
  renombrado e informar el conflicto.
- Cuando un admin renombra una categoría existente, el sistema deberá
  aplicar el cambio de inmediato; como los productos referencian la
  categoría (no copian su nombre), el nuevo nombre se refleja de
  inmediato en todos los productos que la tengan asignada.
- Si dos admins renombran la misma categoría casi al mismo tiempo,
  entonces el sistema deberá aplicar el último cambio guardado (gana el
  más reciente).
- Si un admin intenta eliminar una categoría que tiene al menos un
  producto asignado, entonces el sistema deberá rechazar la eliminación e
  indicar que debe reasignar esos productos a otra categoría primero.
- Si un admin intenta eliminar una categoría sin ningún producto
  asignado, entonces el sistema deberá eliminarla definitivamente.

### RF-2 — Creación de productos por el admin

- Cuando un admin crea un producto con nombre, categoría, precio y
  disponibilidad, el sistema deberá guardarlo en el catálogo.
- El sistema deberá siempre exigir que la categoría del producto
  corresponda a una categoría ya existente, seleccionada de una lista;
  nunca se ingresa como texto libre.
- Si todavía no existe ninguna categoría creada, entonces el sistema
  deberá rechazar la creación del producto e indicar que primero debe
  crearse al menos una categoría (RF-1).
- El sistema deberá siempre exigir que el nombre del producto no esté
  vacío y tenga como máximo 100 caracteres.
- Si el nombre del producto ya existe en el catálogo (ignorando
  mayúsculas y minúsculas), entonces el sistema deberá rechazar la
  creación e informar el conflicto.
- El sistema deberá siempre exigir que el precio sea un valor numérico
  mayor que cero.
- Si el admin no especifica disponibilidad al crear el producto, el
  sistema deberá crearlo como disponible por defecto.

### RF-3 — Edición de productos existentes

- Cuando un admin edita el nombre, la categoría o el precio de un
  producto, el sistema deberá aplicar el cambio de inmediato.
- Al reasignar la categoría de un producto, el sistema deberá exigir que
  la nueva categoría corresponda a una ya existente (RF-1), igual que en
  la creación (RF-2).
- Al editar el nombre de un producto, el sistema deberá exigir la misma
  unicidad que en la creación (RF-2): si el nuevo nombre ya existe en
  otro producto (ignorando mayúsculas y minúsculas), la edición se
  rechaza.
- Un cambio de precio deberá afectar únicamente a partir de los próximos
  pedidos que incluyan ese producto; las líneas ya agregadas a pedidos
  abiertos con el precio anterior no se modifican (regla que el módulo de
  pedidos debe respetar al registrar el precio de cada línea).
- Si dos admins editan el mismo producto casi al mismo tiempo, entonces el
  sistema deberá aplicar el último cambio guardado (gana el más reciente).

### RF-4 — Disponibilidad del producto

- Cuando un admin marca un producto como no disponible, el sistema deberá
  impedir que se agregue a pedidos nuevos a partir de ese momento, sin
  afectar los pedidos ya abiertos que ya lo incluyen.
- Cuando un admin marca un producto como disponible nuevamente, el sistema
  deberá permitir volver a agregarlo a pedidos nuevos.
- Mientras un producto esté marcado como no disponible, el sistema deberá
  excluirlo por completo de la lectura de menú que consulta el mesero
  (RF-7); solo el admin lo sigue viendo en el panel para poder
  reactivarlo.

### RF-5 — Eliminación definitiva de productos

- Cuando un admin elimina un producto, el sistema deberá eliminarlo
  definitivamente del catálogo, sin importar si tuvo o no pedidos en el
  pasado.
- El historial de pedidos no depende de que el producto siga existiendo:
  cada línea de pedido conserva su propia copia del nombre y el precio del
  producto al momento de agregarse (ver RF-3), no una referencia en vivo
  al producto — así que eliminarlo no afecta ningún pedido pasado ni
  presente.
- Si el admin necesita el producto de nuevo más adelante, deberá crearlo
  como un producto nuevo (RF-2); el sistema no ofrece recuperar uno ya
  eliminado.

### RF-6 — Propagación en tiempo real del menú

- Cuando un admin crea, edita, cambia la disponibilidad o elimina un
  producto, o renombra una categoría, el sistema deberá notificar el
  cambio en tiempo real a todas las apps de mesero conectadas, sin que el
  mesero deba recargar manualmente.
- Crear o eliminar una categoría sin productos asignados no dispara esta
  notificación en tiempo real: no cambia nada visible para el mesero
  (RF-7), ya que él nunca navega una lista de categorías por sí sola; el
  efecto se nota más adelante, cuando se le asigna un producto, y ese sí
  es un cambio de producto que notifica.
- El sistema deberá ofrecer en la app de mesero una acción manual de
  "Actualizar menú" que vuelva a traer el menú completo bajo demanda, como
  respaldo para cuando la notificación en tiempo real no llegue.

### RF-7 — Lectura del menú por el mesero

- El sistema deberá permitir a un mesero autenticado consultar el menú,
  incluyendo la categoría de cada producto; solo deberá mostrarle los
  productos marcados como disponibles — un producto marcado como no
  disponible desaparece por completo de esta lectura hasta que un admin
  lo vuelva a marcar disponible (RF-4).
- El sistema deberá impedir siempre que un mesero cree, edite o elimine
  una categoría, o cree, edite, cambie la disponibilidad o elimine un
  producto: su acceso al menú es de solo lectura.

### RF-9 — Búsqueda en el menú

*(Agregado 2026-10-12.)*

- El sistema deberá ofrecer, en el menú del mesero y en la gestión de
  productos del admin, una barra de búsqueda por nombre que no distinga
  mayúsculas de minúsculas ni tildes ("cancion" encuentra "Canción"; la
  ñ cuenta como n).
- La búsqueda no oculta productos: resalta la parte del nombre que
  coincide (en el menú del mesero) y la fila completa del producto,
  lleva la pantalla hasta la coincidencia actual, muestra "N de M
  coincidencias" y permite saltar entre ellas (▲ ▼ o Enter). Si no hay
  coincidencias, lo dice.
- Es solo una ayuda de pantalla sobre el menú ya cargado: no cambia
  ningún dato ni ninguna validación del backend.

### RF-8 — Permisos y autenticación

- El sistema deberá exigir siempre una sesión autenticada válida para
  cualquier endpoint de menú o de categorías (lectura o escritura),
  rechazando solicitudes sin sesión.
- Si un mesero autenticado intenta crear, editar, cambiar la
  disponibilidad o eliminar un producto, o crear, editar o eliminar una
  categoría, entonces el sistema deberá rechazar la acción.

## Requisitos no funcionales

- El sistema deberá operar completamente dentro de la red WiFi local del
  restaurante; la consulta y gestión del menú no deberá depender de
  internet (constitución, regla 2).
- El sistema deberá propagar los cambios de menú a los meseros conectados
  en tiempo casi inmediato, acorde a operar sobre red local.
- El sistema deberá almacenar el precio con precisión monetaria suficiente
  para evitar errores de redondeo en el cobro.

## Casos límite

- Admin desactiva un producto que está en un pedido abierto → RF-4 (no
  afecta el pedido en curso; el producto desaparece del menú del mesero,
  pero no de las líneas ya agregadas a ese pedido abierto).
- Cambia el precio de un producto con pedidos abiertos que ya lo incluyen
  → RF-3 (precio congelado en esas líneas).
- Dos admins editan el mismo producto casi al mismo tiempo → RF-3 (gana el
  último guardado).
- Admin elimina un producto que ya tiene pedidos en su historial → RF-5
  (se elimina igual; el historial no depende del producto).
- Mesero pierde la conexión en tiempo real y no recibe la notificación de
  un cambio de menú → RF-6 (botón manual de actualización).
- Admin intenta crear un producto sin que exista ninguna categoría todavía
  → RF-2 (rechazado, debe crear una categoría primero).
- Admin intenta eliminar una categoría que tiene productos asignados →
  RF-1 (rechazado, debe reasignarlos primero).
- Dos admins renombran la misma categoría casi al mismo tiempo → RF-1
  (gana el último guardado).
- Intento de crear/renombrar una categoría a un nombre ya usado (con
  distinta capitalización) → RF-1 (rechazado).
- Dos admins crean, casi al mismo tiempo, dos categorías cuyo nombre
  difiere solo en mayúsculas → RF-1 (la segunda en confirmarse se rechaza
  por duplicado).
- Un admin elimina una categoría mientras otro admin está creando o
  reasignando un producto a esa misma categoría → RF-1/RF-2 (la operación
  que llega después ya no encuentra la categoría y se rechaza).
- Eliminar la última categoría existente (solo posible si no tiene
  productos asignados) deja el catálogo sin categorías → RF-2 (bloquea la
  creación de productos hasta que se cree una nueva categoría).
- Crear un producto con nombre vacío o de más de 100 caracteres → RF-2
  (rechazado).
- Crear un producto o renombrar uno existente con un nombre ya usado por
  otro producto (con distinta capitalización) → RF-2/RF-3 (rechazado).
- Crear un producto con precio menor o igual a cero, o no numérico → RF-2
  (rechazado).
- Crear o renombrar una categoría con nombre vacío o de más de 50
  caracteres → RF-1 (rechazado).
- Mesero intenta crear, editar, cambiar disponibilidad o eliminar un
  producto, o crear, renombrar o eliminar una categoría → RF-7/RF-8
  (rechazado).
- Solicitud sin sesión autenticada a cualquier endpoint de menú o
  categorías → RF-8 (rechazada).
- Admin crea o elimina una categoría sin productos asignados → RF-6 (no
  genera notificación en tiempo real al mesero, porque no hay ningún
  cambio visible para él).

## Fuera de alcance

- Gestión de imágenes de producto.
- Subcategorías o jerarquías de categorías (solo existe un nivel plano de
  categorías, sin anidamiento).
- Orden de visualización, íconos o colores por categoría.
- Control de inventario o stock numérico (la disponibilidad es un
  booleano, no una cantidad).
- Aplicar cambios de precio o disponibilidad a pedidos ya abiertos (regla
  definida aquí, pero implementada por el módulo de pedidos).
- Deshacer o recuperar un producto eliminado definitivamente.
- Historial de cambios de precio, o cualquier registro de auditoría
  (quién/cuándo) sobre creación, edición, disponibilidad o eliminación de
  productos — a diferencia de los pedidos, la gestión del catálogo no
  requiere trazabilidad de auditoría.
- Notas especiales sobre un pedido concreto (p. ej. "sin cebolla", "término
  medio") — no son un dato del producto/catálogo, sino de la línea de un
  pedido específico; pertenecen al módulo de pedidos, junto con el nombre
  y precio congelados de esa línea (ver RF-5).

## Criterios de finalización

- Un admin puede crear una categoría y renombrarla; no puede eliminar una
  que tenga productos asignados.
- Un admin puede crear un producto con nombre único en el catálogo,
  categoría (seleccionada de una lista de categorías existentes), precio
  y disponibilidad desde el panel; nombres duplicados (ignorando
  mayúsculas/minúsculas) se rechazan tanto al crear como al renombrar.
- Un admin puede editar nombre, categoría y precio de un producto
  existente.
- Un admin puede marcar un producto como no disponible y como disponible
  de nuevo, sin afectar pedidos ya abiertos; mientras está no disponible,
  desaparece por completo del menú que consulta el mesero.
- Un admin puede eliminar cualquier producto en cualquier momento, tenga o
  no historial de pedidos, sin que eso afecte los pedidos pasados.
- Un mesero puede consultar el menú completo, pero ninguna acción de
  escritura le es permitida.
- Los cambios de menú visibles para el mesero (productos y renombrado de
  categorías) se propagan en tiempo real a las apps conectadas, y existe
  una acción manual de respaldo para refrescarlo.
- Ningún endpoint de menú funciona sin sesión autenticada, y las acciones
  de escritura rechazan a cualquier cuenta que no sea admin.

## Dudas abiertas

Ninguna pendiente. Quedaron resueltas y ya incorporadas al texto:

- El nombre del producto es único en todo el catálogo, ignorando
  mayúsculas y minúsculas (RF-2, RF-3).
- Un producto no disponible desaparece por completo del menú que
  consulta el mesero, en vez de mostrarse marcado (RF-4, RF-7).
- La propagación en tiempo real (RF-6) solo cubre cambios visibles para
  el mesero (productos, y renombrado de categorías); crear o eliminar una
  categoría vacía no genera notificación.

La gestión del catálogo de menú tampoco requiere trazabilidad de
auditoría (a diferencia de pedidos y cuentas de usuario);
`docs/constitution.md` ya no reclama jurisdicción sobre estas acciones,
así que no hace falta modificarla.
