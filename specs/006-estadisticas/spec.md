# Especificación: Estadísticas

## Contexto y objetivo

El admin necesita, desde el panel de escritorio, consultar cómo va el
negocio a partir de los pedidos y cobros ya registrados: cuánto se ha
producido, en qué cuentas quedó el dinero, cuánto trabajó cada mesero,
y qué productos se venden más. Este módulo es **estrictamente de
lectura** — no crea, corrige ni anula nada; solo agrega y presenta
datos que ya existen gracias a otros módulos.

Depende de [`002-gestion-menu`](../002-gestion-menu/spec.md)
(catálogo de productos — de ahí sale qué es un "producto" para el
ranking de más vendidos), [`003-mesas-pedidos`](../003-mesas-pedidos/spec.md)
(pedidos, ítems, meseros, número del día) y
[`005-cobro`](../005-cobro/spec.md) (cobros, cuentas de pago). No crea
ni modifica ninguna entidad de esos módulos — solo consulta.

Dos fechas distintas conviven en estas estadísticas, y no deben
confundirse: la fecha en que un pedido se **envió** a cocina
(`sent_at`, el mismo día que ya calcula el "número del día" de
[003-RF-14](../003-mesas-pedidos/spec.md)) y la fecha en que un cobro
se **registró** (`charged_at`, 005-RF-3). Cada requisito de este
documento dice explícitamente cuál de las dos usa.

## Usuarios

- **Admin**: el único que consulta estas estadísticas, desde cualquier
  pantalla del panel de escritorio.
- **Mesero**: no tiene acceso a ningún dato de este módulo.

## Historias de usuario

- Como admin, quiero ver cuánto se ha cobrado hoy, para saber cómo va
  el negocio sin tener que sumar manualmente.
- Como admin, quiero ver en qué cuentas quedó ese dinero, para cuadrar
  caja al final del día.
- Como admin, quiero ver cuántos pedidos tomó cada mesero, para
  entender la carga de trabajo de cada uno.
- Como admin, quiero ver los productos más vendidos, para decidir qué
  promocionar o qué dar de baja del menú.
- Como admin, quiero consultar un rango de fechas, para evaluar un
  período más amplio que un solo día.
- Como admin, quiero consultar el detalle de un día específico ya
  pasado, para auditar exactamente qué pedidos y cobros lo compusieron.

## Requisitos funcionales

### RF-1 — Resumen del día

- El sistema deberá mostrar, para una fecha dada (por defecto el día
  de hoy, hora local del restaurante), el total de dinero cobrado ese
  día y la cantidad de pedidos distintos cobrados ese día. El dinero
  cobrado es el neto de cada cobro, ya descontado el descuento que el
  admin haya aplicado ([005 RF-10](../005-cobro/spec.md)).
- "Cantidad de pedidos cobrados" cuenta pedidos, no eventos de cobro:
  un pedido al que se le anuló un cobro y se le volvió a cobrar el
  mismo día (sin importar cuántas veces) cuenta una sola vez.
- El total de dinero y la cantidad de pedidos de un día ya transcurrido
  deberán calcularse según el estado de cada cobro al final de ese día
  (RF-10) — no según su estado actual.
- "Cobrado ese día" se determina siempre por la fecha del cobro
  (`charged_at`) — nunca por la fecha de envío del pedido que se está
  cobrando, ni por ninguna otra fecha del pedido.

### RF-2 — Dinero por cuenta de pago

- El sistema deberá desglosar el dinero cobrado de un día (RF-1) o de
  un rango (RF-5) por cada cuenta de pago (005-RF-2: "Efectivo",
  "Nequi #1234", etc.), mostrando cuánto se recibió en cada una.
- La suma de este desglose deberá coincidir siempre con el total de
  dinero del mismo período (RF-1 o RF-5), incluida la regla de
  estabilidad de días ya transcurridos (RF-10).
- Una cuenta de pago sin ningún cobro en el período consultado no
  deberá aparecer en el desglose.

### RF-3 — Pedidos por mesero

- El sistema deberá mostrar cuántos pedidos envió cada mesero en un día
  dado (por defecto hoy) o en un rango de fechas (RF-5).
- "Enviado ese día"/"en ese rango" se determina siempre por la fecha de
  envío del pedido (`sent_at`, 003-RF-14) — nunca por la fecha de
  cobro.
- El conteo deberá incluir todo pedido enviado en el período sin
  importar su estado final (en preparación, cobrado, o anulado por
  completo); un pedido que nunca se envió (se quedó en "borrador")
  nunca cuenta.
- Un pedido se atribuye siempre al mesero que lo creó
  (`Order.waiter`, dueño fijo e inmutable — 003-RF-7), nunca al admin
  que lo cobró.
- Un mesero sin ningún pedido enviado en el período consultado no
  deberá aparecer en el listado.

### RF-4 — Productos más vendidos

- El sistema deberá mostrar, para un día específico, un rango de
  fechas, o el día actual por defecto, los 10 productos del catálogo
  con más unidades vendidas en ese período, ordenados de mayor a menor
  cantidad.
- Un ítem fuera de carta nunca deberá entrar en este ranking — cubre
  únicamente ítems de catálogo (`OrderItem.catalog_product` no nulo).
- Un ítem anulado (`OrderItem.is_voided = True`), o un ítem que
  pertenece a un pedido anulado por completo
  (`Order.status = VOIDED`, aunque el ítem individualmente no esté
  marcado anulado), nunca deberá contar como vendido.
- Un producto eliminado del catálogo (002-RF-5) deja de contar en el
  ranking desde el momento de su eliminación en adelante: sus ventas
  pasadas ya no se incluyen en ninguna consulta posterior, igual que un
  ítem fuera de carta.
- Toda línea de un pedido (original o adición, sin importar cuántos
  días después del envío se haya agregado) se atribuye al mismo día que
  el envío original del pedido (`sent_at`), nunca a la fecha real en
  que se agregó esa línea — mismo criterio que RF-3, nunca la fecha de
  cobro.

### RF-5 — Filtro por rango de fechas

- El sistema deberá permitir consultar un rango de fechas (desde/hasta,
  ambas inclusive), mostrando la cantidad total de pedidos enviados y
  el dinero total cobrado en ese rango — mismo criterio de fecha por
  métrica que ya definen RF-1 y RF-3 (dinero por fecha de cobro,
  pedidos por fecha de envío).
- El mismo rango deberá exponer también el desglose por cuenta de pago
  (RF-2), por mesero (RF-3), y el ranking de productos más vendidos
  (RF-4) — no solo los dos totales agregados.
- Si la fecha "desde" es posterior a la fecha "hasta", el sistema
  deberá rechazar la consulta.
- Una fecha "hasta" posterior a hoy deberá aceptarse igual que
  cualquier otra; los días del rango que todavía no ocurrieron
  simplemente no aportan pedidos ni dinero.
- El sistema no deberá imponer ningún límite máximo de duración al
  rango.

### RF-6 — Consulta de un día específico (movimiento del día)

- El sistema deberá permitir consultar cualquier día específico (pasado
  o el actual), mostrando dos listas: los pedidos enviados ese día
  (número del día, mesero, estado actual y total) y los cobros
  registrados ese día (cuenta, monto, admin que cobró, y estado —
  activo o anulado).
- El total mostrado de cada pedido es su total **actual** (el que tiene
  en el momento de la consulta) — no se reconstruye cuánto tenía
  exactamente ese día; un pedido que seguía "en preparación" puede
  verse distinto si se vuelve a consultar ese mismo día más adelante.
- Ambas listas deberán incluir pedidos/cobros anulados, para
  trazabilidad — aunque esos registros nunca sumen a ningún total
  (RF-1, RF-2, RF-4), salvo según la regla de estabilidad de RF-10.
- Un cobro anulado un día distinto al que se registró deberá aparecer
  únicamente en el movimiento del día de su `charged_at` original,
  mostrando su estado actual (anulado); su anulación no genera una
  entrada aparte en el día en que ocurrió esa anulación.
- Un día sin ningún pedido enviado ni ningún cobro registrado deberá
  mostrar ambas listas vacías y los totales en cero, nunca un error.

### RF-7 — Identificación de pedidos

- El sistema deberá usar siempre el identificador interno del pedido
  como llave para calcular y relacionar estas estadísticas (incluido
  cruzar pedidos con sus cobros) — nunca el número del día.
- Toda pantalla de este módulo que liste pedidos individuales (RF-6)
  deberá identificarlos por su número del día (003-RF-14), nunca por
  su identificador interno como texto visible. El caso transitorio de
  pedidos sin número del día (003-RF-14, previos a ese despliegue) no
  requiere una regla especial aquí — son anteriores a este módulo.

### RF-8 — Permisos

- El sistema deberá restringir el acceso a cualquier estadística de
  este módulo exclusivamente a admin.
- Si un mesero autenticado intenta acceder a cualquier endpoint de este
  módulo, entonces el sistema deberá rechazar la solicitud.

### RF-9 — Alcance de solo lectura

- El sistema deberá garantizar que ningún endpoint de este módulo
  modifique `Order`, `OrderItem`, `Payment` ni `PaymentAccount` — es
  estrictamente de consulta.

### RF-10 — Estabilidad de los días ya cerrados

- Los totales de dinero y de pedidos cobrados de un día ya transcurrido
  (RF-1, RF-2, RF-5) deberán quedar fijos para siempre: una vez que ese
  día termina, anular un cobro registrado ese día en una fecha
  posterior no deberá cambiar los totales ya reportados para ese día en
  ninguna consulta futura.
- Un cobro anulado el **mismo día** en que se registró sigue sin sumar
  a ese día (coherente con RF-1) — la estabilidad solo protege un día
  que ya cerró, no corrige del mismo día mientras sigue en curso.
- Esta regla no aplica a "pedidos por mesero" (RF-3) ni a "productos
  más vendidos" (RF-4): esas dos métricas se basan en la fecha de envío
  del pedido, que es inmutable desde el momento en que se envía (no
  dependen del estado de ningún cobro).

## Requisitos no funcionales

- El sistema deberá calcular los límites de cada día con la hora local
  del restaurante (`America/Bogota`), el mismo criterio que ya define
  003-RF-14 — nunca en UTC.
- El sistema deberá operar completamente dentro de la red WiFi local
  del restaurante (constitución, regla 2); ninguna consulta de este
  módulo deberá depender de internet.
- El sistema deberá calcular estas estadísticas sin infraestructura
  adicional (constitución, regla 1) mientras el volumen de datos lo
  permita — sobre las tablas ya existentes de 002/003/005; si el
  volumen histórico llegara a exigir algún tipo de precálculo, esa
  decisión de diseño pertenece a `plan.md`, no a este documento.
- El sistema no deberá garantizar una vista transaccionalmente
  consistente entre dos consultas distintas hechas en momentos
  diferentes (ej. consultar el resumen del día justo mientras se
  registra un cobro) — cada consulta refleja el estado de la base de
  datos en el instante en que se ejecuta, igual que cualquier reporte
  sobre datos en vivo.

## Casos límite

- Un pedido se envía un día y se cobra al día siguiente → RF-1, RF-3
  (el pedido cuenta para "pedidos por mesero" del día en que se
  envió; el dinero cuenta para el resumen y el desglose del día en que
  se cobró — pueden ser días distintos).
- Un pedido se envía y nunca se cobra (sigue en preparación, o se anula
  antes de cobrarse) → RF-3 (cuenta igual como pedido tomado por su
  mesero); RF-1, RF-2 (nunca aporta dinero a ningún día).
- Un cobro se anula y se vuelve a cobrar con otra cuenta el mismo día →
  RF-1, RF-2 (el total de ese día refleja solo el cobro activo final;
  el anulado no suma; el pedido sigue contando una sola vez, RF-1).
- Un cobro se anula un día **distinto** al que se registró, después de
  que ese día ya cerró → RF-10 (el total ya reportado para el día
  original del cobro no cambia); RF-6 (el movimiento de ese día
  original lo sigue mostrando, ahora marcado como anulado).
- Un pedido completo se anula (003-RF-11) después de haber tenido
  adiciones → RF-3 (cuenta igual como pedido tomado); RF-4 (ninguno de
  sus ítems, originales o adiciones, cuenta como vendido).
- Se vende un ítem fuera de carta → RF-4 (nunca aparece en el ranking
  de productos más vendidos, aunque sí cuenta en el dinero/pedidos del
  día si el pedido se cobra).
- Una adición se agrega varios días después del envío original del
  pedido → RF-3, RF-4 (se atribuye al día del envío original, nunca al
  día real en que se agregó esa línea).
- Se consulta un rango con "desde" posterior a "hasta" → RF-5
  (rechazado).
- Se consulta un rango cuya fecha "hasta" es futura → RF-5 (aceptado;
  los días futuros simplemente no aportan datos).
- Se consulta un día sin ningún movimiento → RF-6 (listas vacías,
  totales en cero, sin error).
- Un producto se elimina del catálogo después de haberse vendido →
  RF-4 (deja de contar en el ranking desde ese momento en adelante;
  sus ventas pasadas ya no se incluyen en ninguna consulta posterior).
- Un mesero intenta acceder a cualquier endpoint de este módulo → RF-8
  (rechazado).

## Fuera de alcance

- Registrar o corregir cobros — pertenece a
  [005-cobro](../005-cobro/spec.md).
- Crear, editar o anular pedidos — pertenece a
  [003-mesas-pedidos](../003-mesas-pedidos/spec.md).
- Cualquier acceso a estas estadísticas desde fuera de la red local del
  restaurante (constitución, regla 2).
- Exportar reportes a PDF/CSV o cualquier otro formato de archivo.
- Gráficas, dashboards visuales o cualquier otra forma de presentación
  — este documento define qué datos deben poder consultarse, no cómo
  se dibujan.
- Comparaciones automáticas entre períodos (ej. "esta semana vs. la
  anterior") o cualquier proyección de ventas futuras.
- Estadísticas por mesa, por categoría de producto, por hora del día, o
  cualquier otro corte no listado explícitamente en este documento.
- Notificaciones o alertas basadas en estas estadísticas.

## Criterios de finalización

- El admin puede consultar, sin pasar ningún parámetro, el dinero
  cobrado hoy, su desglose por cuenta de pago, cuántos pedidos tomó
  cada mesero hoy, y los 10 productos más vendidos hoy.
- El admin puede consultar un rango de fechas arbitrario y obtener el
  total de pedidos enviados, el dinero cobrado, el desglose por cuenta
  y mesero, y el ranking de productos más vendidos de ese rango.
- El admin puede consultar cualquier día específico, pasado o actual,
  y ver el movimiento completo de pedidos y cobros de ese día,
  incluidos los anulados.
- Ningún total se infla por ítems o cobros anulados; el movimiento del
  día los sigue mostrando, para trazabilidad.
- Los totales de dinero de un día ya transcurrido no cambian aunque,
  tiempo después, se anule un cobro registrado ese día.
- Ningún pedido se identifica por su identificador interno en ninguna
  pantalla de este módulo.
- Un mesero no puede acceder a ningún endpoint de este módulo.
- Ningún endpoint de este módulo modifica ningún registro existente.

## Dudas abiertas

Ninguna pendiente. Quedaron resueltas y ya incorporadas:

- El dinero (RF-1, RF-2, RF-5) se agrupa por la fecha del cobro
  (`charged_at`), nunca por la fecha de envío del pedido.
- Los pedidos por mesero (RF-3) se agrupan por la fecha de envío
  (`sent_at`), y cuentan todo pedido enviado ese día sin importar si
  después se anuló o si todavía no se ha cobrado.
- Los ítems fuera de carta quedan completamente excluidos del ranking
  de productos más vendidos (RF-4) — nunca se agrupan por nombre ni
  aparecen como una entrada genérica.
- El ranking de productos más vendidos (RF-4) se ordena por cantidad de
  unidades vendidas, no por dinero facturado, y muestra como máximo los
  10 primeros.

De la auditoría QA posterior sobre este módulo, quedaron resueltas y ya
incorporadas:

- "Cantidad de pedidos cobrados" (RF-1) cuenta pedidos distintos, no
  eventos de cobro — un pedido anulado y vuelto a cobrar el mismo día
  cuenta una sola vez.
- Una adición agregada días después del envío original se atribuye
  siempre al día del envío original del pedido, tanto para "pedidos por
  mesero" (RF-3) como para "productos más vendidos" (RF-4).
- "Pedidos por mesero" (RF-3) también se expone para un rango de
  fechas (RF-5), no solo para un día puntual.
- Una fecha "hasta" futura en el rango (RF-5) se acepta igual que
  cualquier otra; los días que todavía no ocurrieron no aportan datos.
- El total de cada pedido en el movimiento del día (RF-6) es su total
  actual, no un snapshot congelado a esa fecha.
- Este módulo no necesita estadísticas por mesa — se eliminó ese campo
  del movimiento del día (RF-6) y se agregó a "Fuera de alcance".
- Un producto eliminado del catálogo deja de contar en el ranking de
  productos más vendidos (RF-4) desde su eliminación en adelante — no
  se agrega ningún campo nuevo al modelo de `OrderItem` para
  distinguir su origen histórico.
- Los pedidos sin número del día (caso transitorio de 003-RF-14) no
  necesitan una regla especial en este módulo (RF-7) — son anteriores
  a su existencia.
- Los totales de un día ya transcurrido quedan fijos para siempre
  (RF-10, nuevo): anular un cobro de un día anterior no cambia
  retroactivamente los totales ya reportados de ese día.
- No se amplía la regla 5 de `docs/constitution.md` para cubrir
  restricciones de lectura — RF-8 basta por sí solo.
