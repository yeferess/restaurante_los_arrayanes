# 001 · Autenticación y gestión de usuarios

## Contexto y objetivo

El sistema tiene dos roles, admin y mesero, con dos puntos de entrada
separados (`/admin` y `/mesero`) a la misma aplicación. El objetivo de este
módulo es permitir que cada rol se autentique solo en su punto de entrada, y
que el admin gestione el ciclo de vida de las cuentas de mesero (creación,
restablecimiento de PIN, activación/desactivación) sin poder alterar su
historial, en línea con la regla de trazabilidad de
[`docs/constitution.md`](../../docs/constitution.md). Este módulo es la base
de permisos sobre la que se apoyan todos los demás (pedidos, cobro, etc.).

## Usuarios

- **Admin**: gestiona el restaurante desde el panel de escritorio (`/admin`).
  Puede haber varias cuentas admin simultáneas.
- **Mesero**: toma pedidos desde la PWA (`/mesero`). Su cuenta la crea y
  gestiona un admin; el mesero no se autogestiona.
- **Operador técnico**: persona con acceso físico/remoto al servidor del
  restaurante. No es un rol de la aplicación; actúa solo mediante comandos en
  la terminal del servidor para tareas que ningún admin puede hacer desde la
  web (creación del primer admin, recuperación de acceso de un admin).

## Historias de usuario

- Como mesero, quiero iniciar sesión con mi usuario y PIN desde `/mesero`,
  para acceder solo a las funciones de mi rol durante mi turno.
- Como admin, quiero iniciar sesión desde `/admin` con usuario y contraseña,
  para gestionar el restaurante sin que esa pantalla sea visible para los
  meseros.
- Como admin, quiero crear la cuenta de un nuevo mesero con un PIN simple,
  para que pueda empezar a tomar pedidos de inmediato.
- Como admin, quiero restablecer el PIN de un mesero que lo olvidó sin poder
  alterar ningún otro dato de su cuenta, para resolver el problema sin
  comprometer la trazabilidad de su historial.
- Como admin, quiero desactivar la cuenta de un mesero que ya no trabaja
  aquí, para revocar su acceso sin borrar ni editar su historial de
  acciones pasadas.
- Como operador técnico, quiero crear la primera cuenta admin desde el
  servidor al instalar el sistema, para empezar a usarlo sin depender de
  credenciales predefinidas conocidas por cualquiera.
- Como admin, quiero que mi sesión expire tras un rato de inactividad, para
  reducir el riesgo si dejo el panel desatendido.
- Como mesero, quiero que mi sesión no se cierre sola durante el turno, para
  no perder tiempo reingresando el PIN entre pedidos.

## Requisitos funcionales

### RF-1 — Login diferenciado por punto de entrada y rol

- Cuando un usuario accede a `/admin`, el sistema deberá mostrar únicamente
  el formulario de login para el rol admin.
- Cuando un usuario accede a `/mesero`, el sistema deberá mostrar únicamente
  el formulario de login para el rol mesero.
- Si una cuenta de rol mesero intenta autenticarse en `/admin`, entonces el
  sistema deberá rechazar el acceso sin revelar si el usuario existe.
- Si una cuenta de rol admin intenta autenticarse en `/mesero`, entonces el
  sistema deberá rechazar el acceso sin revelar si el usuario existe. 
- Si una cuenta de mesero está bloqueada por intentos fallidos (RF-7), el
  sistema deberá mostrar el mensaje "Tu cuenta está bloqueada. Habla con un
  administrador para resolverlo.", como excepción explícita a la regla de
  no revelar si el usuario existe.
- Si una cuenta admin está bloqueada por intentos fallidos (RF-7), el
  sistema deberá mostrar el mensaje "Tu cuenta está bloqueada. Espera 20
  minutos o contacta al operador técnico del sistema.", reflejando las
  únicas dos vías reales de desbloqueo definidas en RF-7.
- Si una cuenta de mesero está desactivada (RF-5), el sistema deberá
  mostrar el mensaje "Tu cuenta está desactivada. Habla con un
  administrador para resolverlo.", como la misma excepción explícita.
- Si una cuenta admin está desactivada permanentemente (RF-10), el sistema
  deberá mostrar el mensaje "Tu cuenta fue desactivada permanentemente.
  Contacta al operador técnico si necesitas una cuenta nueva.", como la
  misma excepción explícita (esta cuenta no tiene reactivación posible,
  ver RF-10).
- Si el intento de login falla por usuario o credencial incorrecta (cuenta
  inexistente, o existente pero no bloqueada ni desactivada), el sistema
  deberá mostrar "Usuario o contraseña incorrectos. Te quedan N intentos
  antes del bloqueo.", mostrando el conteo de intentos restantes según el
  umbral de RF-7. Para no romper la regla de no revelar si el usuario
  existe, el sistema deberá mostrar este conteo de forma consistente
  también cuando el usuario no exista (simulando el mismo descenso de
  intentos que vería una cuenta real).

### RF-2 — Creación de cuentas de mesero por el admin

- Cuando un admin crea una cuenta de mesero con usuario y PIN, el sistema
  deberá guardarla como activa y registrar qué admin la creó.
- El sistema deberá siempre exigir que el PIN tenga entre 4 y 6 dígitos
  numéricos ingresados por el admin.
- Si el nombre de usuario ya existe (entre cuentas admin y cuentas mesero,
  ya que la unicidad es global), entonces el sistema deberá rechazar la
  creación e informar el conflicto.
- El sistema deberá exigir que el nombre de usuario tenga entre 3 y 20
  caracteres, use solo letras, números y guion bajo (sin espacios ni
  símbolos), y deberá tratarlo sin distinguir mayúsculas de minúsculas
  para todo efecto (creación, duplicados y login). Esta regla de formato y
  unicidad es global: aplica a todo nombre de usuario del sistema, sea de
  cuenta admin o mesero, sin importar qué requisito describa su creación.

### RF-3 — Restricción de edición sobre una cuenta de mesero ya creada

- El sistema deberá siempre impedir que un admin edite el nombre de usuario
  u otros datos identificatorios de una cuenta de mesero ya creada.
- El sistema deberá permitir al admin únicamente tres acciones sobre una
  cuenta de mesero existente: restablecer el PIN, activarla/desactivarla
  (RF-5), y desbloquearla tras un bloqueo por intentos fallidos (RF-7).
  "Bloqueada" y "desactivada" son estados distintos entre sí e
  independientes: el admin puede desactivar directamente a un mesero
  bloqueado, sin necesidad de desbloquearlo primero.

### RF-4 — Restablecimiento de PIN de mesero

- Cuando un admin restablece el PIN de un mesero, el sistema deberá
  invalidar el PIN anterior de inmediato.
- Cuando un admin restablece el PIN de un mesero, el sistema deberá
  registrar qué admin lo hizo y cuándo.
- Cuando un admin restablece el PIN de un mesero, el sistema deberá cerrar
  cualquier sesión activa de ese mesero en cualquier dispositivo.
- Si dos admins restablecen el PIN del mismo mesero casi al mismo tiempo,
  entonces el sistema deberá aplicar el último restablecimiento recibido
  (gana el más reciente), y deberá registrar ambos eventos en la traza
  (RF-11).

### RF-5 — Desactivación y reactivación de cuentas de mesero

- Cuando un admin desactiva una cuenta de mesero, el sistema deberá impedir
  nuevos inicios de sesión de esa cuenta desde ese momento.
- Si el mesero tiene mesas o pedidos abiertos al momento de intentar la
  desactivación, entonces el sistema deberá rechazar la desactivación e
  informar qué debe cerrarse primero.
- El sistema deberá siempre conservar sin modificar el historial de acciones
  de una cuenta desactivada.
- El sistema deberá permitir a un admin reactivar una cuenta de mesero
  previamente desactivada.

### RF-6 — Aislamiento entre cuentas admin

- El sistema deberá permitir que un admin cambie su propia contraseña desde
  el panel web, exigiendo un mínimo de 8 caracteres que combinen al menos
  letras y números (misma regla de complejidad que RF-10 exige al crear o
  cambiar cualquier contraseña de admin).
- El sistema deberá siempre impedir que un admin edite la contraseña, el
  estado u otro dato de **otra** cuenta admin desde el panel web (crear una
  cuenta admin nueva no se considera edición, ver RF-10).
- El sistema deberá siempre impedir que un admin edite el nombre de usuario
  de cualquier cuenta admin desde el panel web, incluida la suya propia
  (esa edición solo es posible mediante comando de servidor, ver RF-10).
- El sistema deberá siempre permitir que exista más de una cuenta con rol
  admin de forma simultánea.
- El sistema deberá siempre garantizar que exista al menos una cuenta admin
  activa. Si una acción (por ejemplo, la desactivación permanente por
  comando de servidor de RF-10) dejaría cero cuentas admin activas,
  entonces el sistema deberá rechazarla.
  
### RF-7 — Bloqueo por intentos fallidos de login

- Cuando una cuenta (admin o mesero) acumula **5 intentos fallidos
  consecutivos** de login, el sistema deberá bloquearla de inmediato e
  impedir nuevos intentos de autenticación, sin importar si el mesero tiene
  mesas o pedidos abiertos (a diferencia de la desactivación de RF-5, este
  bloqueo es automático y no admite excepciones).
- Cuando un admin desbloquea una cuenta de mesero bloqueada por intentos
  fallidos, el sistema deberá exigir que ese mismo acto incluya el
  restablecimiento del PIN (RF-4): no se permite desbloquear sin asignar un
  PIN nuevo.
- Cuando una cuenta admin queda bloqueada por intentos fallidos, el sistema
  deberá desbloquearla automáticamente **20 minutos** después del último
  intento fallido, sin requerir intervención de otro admin.
- Si el operador técnico ejecuta el comando de recuperación de acceso
  (RF-10) sobre una cuenta admin bloqueada, entonces el sistema deberá
  desbloquearla de inmediato, sin esperar los 20 minutos.
- Un bloqueo temporal por intentos fallidos no cuenta como "cuenta admin
  inactiva" a efectos de la garantía de RF-6: se resuelve solo (20 minutos)
  o por el operador técnico, y no requiere que exista otra cuenta admin
  activa mientras dure.
- Cuando una cuenta cualquiera hace un login exitoso dentro de los 5 intentos
  permitidos, el contador de intentos fallidos se resetea a 0.
- El sistema deberá siempre registrar cada intento fallido de login (cuenta,
  fecha y hora) para trazabilidad.
- Cuando una cuenta (admin o mesero) quede bloqueada por intentos fallidos,
  el sistema deberá invalidar de inmediato cualquier sesión activa de esa
  cuenta en cualquier dispositivo, obligando a iniciar sesión nuevamente
  una vez desbloqueada.
- El bloqueo de sesión no deberá eliminar el borrador de pedido que el
  mesero tuviera sin enviar — ese borrador permanece guardado localmente
  en su dispositivo hasta que vuelva a iniciar sesión

### RF-8 — Sesión de admin con expiración por inactividad

- El sistema deberá siempre cerrar la sesión de un admin tras 30 minutos
  consecutivos de inactividad.
- Cuando la sesión de un admin expira por inactividad, el sistema deberá
  exigir usuario y contraseña completos de nuevo antes de permitir cualquier
  acción.
- El sistema deberá considerar como "actividad" del admin cualquier
  movimiento de mouse, clic, tecla presionada, scroll o toque dentro de la
  ventana del panel administrativo — no solo la navegación entre pantallas
  o el envío de formularios.
- Si transcurren 30 minutos sin ningún evento de actividad detectado, el
  sistema deberá cerrar la sesión del admin automáticamente.

### RF-9 — Sesión de mesero persistente durante el turno

- El sistema deberá siempre mantener la sesión de un mesero activa hasta que
  se cierre sesión manualmente en el dispositivo, sin expirar por
  inactividad, salvo que otro requisito de esta especificación exija
  cerrarla explícitamente (por ejemplo, RF-4 al restablecer el PIN, o RF-7
  al bloquear la cuenta por intentos fallidos).
- El sistema deberá permitir una sola sesión activa por mesero a la vez.
  Cuando un mesero inicia sesión en un dispositivo nuevo, el sistema deberá
  invalidar automáticamente cualquier sesión previa de esa misma cuenta en
  otro dispositivo.
- Cuando un mesero cierra sesión manualmente, el sistema deberá invalidar la
  sesión de ese dispositivo de inmediato.



### RF-10 — Creación del primer admin y recuperación de acceso admin

- Cuando el sistema se instala y no existe ninguna cuenta admin, el sistema
  deberá requerir un comando ejecutado en el servidor para crear la primera
  cuenta admin, antes de permitir el uso de `/admin`.
- El sistema deberá permitir que cualquier admin ya autenticado cree cuentas
  admin adicionales desde el panel web, ingresando usuario y contraseña
  inicial en el mismo formulario de creación (igual que el admin ingresa el
  PIN de un mesero en RF-2).
- El sistema deberá exigir que toda contraseña de admin (al crearla o al
  cambiarla) tenga un mínimo de 8 caracteres y combine al menos letras y
  números.
- El sistema deberá permitir desactivar de forma permanente una cuenta
  admin (sin posibilidad de reactivarla), recuperar su acceso (contraseña
  olvidada), o desbloquearla de inmediato si está bloqueada por intentos
  fallidos (RF-7), exclusivamente mediante un comando ejecutado en el
  servidor — nunca desde el panel web. Cuando el operador técnico desactiva
  permanentemente una cuenta admin, el sistema deberá invalidar de
  inmediato cualquier sesión activa de esa cuenta. "Eliminar" una cuenta
  admin nunca borra el registro ni sus datos: solo la desactiva, para
  preservar intactas todas las referencias de trazabilidad (RF-2, RF-4,
  RF-5, RF-6,
  RF-11) que la mencionan como ejecutora de una acción pasada.
- El sistema deberá permitir cambiar el nombre de usuario de una cuenta
  admin (incluida la del propio operador técnico) exclusivamente mediante
  un comando ejecutado en el servidor, respetando las mismas reglas de
  formato y unicidad definidas en RF-2. Si el nombre solicitado ya está en
  uso por otra cuenta (admin o mesero), el comando deberá rechazar el
  cambio, igual que lo haría el panel web. Cuando el operador técnico
  cambia el nombre de usuario de un admin con sesión activa, el sistema
  deberá invalidar esa sesión de inmediato, obligándolo a iniciar sesión
  de nuevo con el nombre de usuario actualizado.


### RF-11 — Trazabilidad de acciones sobre cuentas de mesero

- El sistema deberá siempre registrar, para cada creación, restablecimiento
  de PIN, activación, desactivación o desbloqueo de una cuenta de mesero:
  qué admin la ejecutó, cuándo, y sobre qué cuenta.

## Requisitos no funcionales

- El sistema deberá siempre almacenar contraseñas y PINs de forma cifrada,
  nunca en texto plano.
- El sistema deberá siempre operar completamente dentro de la red WiFi
  local del restaurante, sin requerir internet para ningún flujo de login o
  gestión de usuarios (constitución, regla 2).
- El sistema deberá siempre responder al login en tiempo casi inmediato,
  acorde a operar sobre red local sin salto a internet.
- Los mensajes de error de login no deberán revelar si el usuario existe,
  para no facilitar enumeración de cuentas, salvo la excepción explícita de
  RF-1 para cuentas bloqueadas o desactivadas.

## Casos límite

Ninguno pendiente. Los casos identificados quedaron cubiertos por un
requisito funcional específico:

- Admin cambia su propia contraseña → RF-6.
- Único admin activo del sistema → RF-6, RF-7.
- Mesero pierde conexión sin logout explícito → RF-9.
- Dos admins restablecen el PIN del mismo mesero casi al mismo tiempo → RF-4.
- Servidor se reinicia sin conexión a internet → NFR de operación en LAN.
- Mesero desactivado intenta iniciar sesión → RF-5.
- Mesero bloqueado por intentos fallidos con mesas/pedidos abiertos → RF-7.
- Admin desactivado permanentemente con sesión activa → RF-10.
- Operador técnico renombra un admin a un username ya usado → RF-10.
- Operador técnico renombra a un admin con sesión activa → RF-10.
- Admin desactiva directamente a un mesero bloqueado, sin desbloquearlo
  antes → RF-3.

## Fuera de alcance

- Recuperación de contraseña por autoservicio (tipo "olvidé mi contraseña"),
  por correo o SMS, para cualquier rol.
- Autenticación de dos factores (2FA).
- Reasignación de mesas/pedidos de un mesero desactivado (pertenece al
  módulo de pedidos/mesas).
- Cobro y liquidación de mesas (pertenece a otro módulo; aquí solo se define
  que es exclusivo del rol admin).
- Múltiples locales o sucursales (fuera del alcance del proyecto completo,
  no solo de este módulo).
- Inicio de sesión social o SSO externo.

## Criterios de finalización

- Un admin puede loguearse en `/admin` y un mesero en `/mesero`, cada uno
  solo con credenciales de su propio rol.
- Un admin puede crear una cuenta de mesero con PIN, y esa cuenta puede
  loguearse de inmediato en `/mesero`.
- Un admin puede restablecer el PIN de un mesero; el mesero puede loguearse
  con el nuevo PIN y ya no con el anterior.
- Ningún admin puede editar el nombre de usuario u otros datos de una cuenta
  de mesero ya creada desde ninguna pantalla del panel.
- Un admin puede desactivar un mesero sin mesas abiertas; la cuenta
  desactivada no puede volver a loguearse.
- Intentar desactivar un mesero con mesas abiertas es rechazado con un
  mensaje claro de qué falta cerrar.
- Toda creación, restablecimiento de PIN, activación o desactivación de
  mesero queda registrada con el admin ejecutor y la fecha/hora.
- Ningún admin puede modificar la cuenta de otro admin desde el panel web.
- El sistema rechaza cualquier acción que dejaría el sistema sin ninguna
  cuenta admin activa.
- El sistema funciona de punta a punta sin conexión a internet, solo con la
  red LAN del restaurante.

## Dudas abiertas

Ninguna pendiente. Todas las dudas iniciales quedaron resueltas en los
requisitos funcionales correspondientes.
