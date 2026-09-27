# 001 · Autenticación y gestión de usuarios — Tareas

Basado en `spec.md` (requisitos) y `plan.md` (diseño técnico). Cada tarea
es de ~20-30 min, están en orden de dependencia (no empezar una tarea sin
que las anteriores estén hechas). Cada una indica el/los RF que cubre y una
condición verificable de "Hecho cuando".

---

## Fase 0 — Setup del módulo

- [x] **T01 — Crear la app `accounts`**
  RF: — (infraestructura)
  Hecho cuando: existe `apps/accounts/` con la estructura de `plan.md`
  (sección 1), está en `INSTALLED_APPS`, y `python manage.py check` no
  reporta errores.

- [x] **T02 — Configurar sesiones de Django (cookie httpOnly)**
  RF: soporte de RF-8, RF-9 (NFR de cifrado/LAN)
  Hecho cuando: `SESSION_COOKIE_HTTPONLY=True`,
  `SESSION_COOKIE_SAMESITE='Strict'` y el backend de sesión apuntan a la
  base SQLite del proyecto en `settings.py`.

---

## Fase 1 — Modelo de datos

- [x] **T03 — Modelo `Usuario` base**
  RF: RF-1, RF-2
  Hecho cuando: existe el modelo con `username`, `role`
  (`ADMIN`/`MESERO`), `password_hash` vía `AbstractBaseUser`, `is_active`;
  la migración corre sin errores (`makemigrations` + `migrate`).

- [x] **T04 — Campos de bloqueo en `Usuario`**
  RF: RF-7
  Hecho cuando: `is_locked`, `locked_at`, `failed_login_attempts` existen
  en el modelo con los defaults de `plan.md` sección 2, y la migración
  aplica sin errores.

- [x] **T05 — Campos `current_session_key` y `created_by`**
  RF: RF-9, RF-2, RF-6, RF-11
  Hecho cuando: ambos campos existen (`created_by` como FK a sí mismo con
  `on_delete=PROTECT`), y la migración aplica sin errores.

- [x] **T06 — Modelo `AccionCuenta`**
  RF: RF-11
  Hecho cuando: existe el modelo con los campos de `plan.md` sección 2
  (`cuenta`, `tipo_accion`, `ejecutado_por`, `via_cli`, `timestamp`), y la
  migración aplica sin errores.

- [x] **T07 — Modelo `IntentoFallido`**
  RF: RF-7
  Hecho cuando: existe el modelo (`cuenta`, `timestamp`), y la migración
  aplica sin errores.

- [x] **T08 — Validador de `username`**
  RF: RF-2
  Hecho cuando: un test manual (shell de Django) confirma que un username
  de 2 caracteres, uno de 21, uno con espacios o símbolos, y uno duplicado
  (ignorando mayúsculas) son todos rechazados por el modelo/serializer.

- [x] **T09 — Validadores de PIN y de contraseña admin**
  RF: RF-2, RF-6, RF-10
  Hecho cuando: un PIN de 3 o de 7 dígitos es rechazado; un PIN no numérico
  es rechazado; una contraseña de admin de menos de 8 caracteres o sin
  combinar letras y números es rechazada.

---

## Fase 2 — Servicios de negocio (`services.py`)

- [x] **T10 — `registrar_accion()`**
  RF: RF-11
  Hecho cuando: llamar la función crea una fila en `AccionCuenta` con
  `cuenta`, `tipo_accion`, `ejecutado_por` y `timestamp` correctos
  (verificado en shell de Django).

- [x] **T11 — `intentar_login()` básico (sin bloqueo todavía)**
  RF: RF-1
  Hecho cuando: dado un username y credencial correctos devuelve éxito;
  dado uno incorrecto devuelve el mensaje genérico de RF-1 sin distinguir
  si el username existe.

- [x] **T12 — Bloqueo tras 5 intentos fallidos**
  RF: RF-7
  Hecho cuando: 5 intentos fallidos consecutivos dejan `is_locked=True` y
  `locked_at` seteado; un 6º intento con credencial correcta sigue
  rechazado por estar bloqueada.

- [x] **T13 — Reseteo del contador tras login exitoso**
  RF: RF-7
  Hecho cuando: 3 intentos fallidos seguidos de 1 exitoso dejan
  `failed_login_attempts == 0`.

- [x] **T14 — Auto-desbloqueo perezoso de admin (20 min)**
  RF: RF-7
  Hecho cuando: una cuenta admin con `locked_at` de hace 21 minutos
  (simulado) se desbloquea sola al siguiente intento de login, sin que
  nadie la haya tocado.

- [x] **T15 — Mensajes diferenciados por estado y rol (RF-1)**
  RF: RF-1
  Hecho cuando: existen las 5 combinaciones de mensaje exactas de
  `spec.md` RF-1 (bloqueada mesero, bloqueada admin, desactivada mesero,
  desactivada admin, credenciales inválidas) y cada una se dispara en el
  escenario correcto.

- [x] **T16 — Conteo simulado para username inexistente**
  RF: RF-1
  Hecho cuando: un login con un username que no existe devuelve el mismo
  formato de mensaje ("Te quedan N intentos...") que uno real, sin
  persistir ninguna fila en `IntentoFallido`.

- [x] **T17 — Invalidar sesión previa del mesero (sesión única)**
  RF: RF-9
  Hecho cuando: loguear al mismo mesero dos veces seguidas dejar la
  primera sesión inválida (un request con la cookie vieja devuelve 401).

- [x] **T18 — `garantizar_admin_activo()`**
  RF: RF-6
  Hecho cuando: con un solo admin activo en la base, la función rechaza
  (lanza excepción/retorna False) cualquier intento de dejarlo inactivo; con
  dos o más admins activos, lo permite.

---

## Fase 3 — Endpoints de la API

- [x] **T19 — Serializers y permisos base (`EsAdmin`, `EsMesero`)**
  RF: RF-1
  Hecho cuando: existen ambas clases de permiso y devuelven 403 si el rol
  de `request.user` no coincide.

- [x] **T20 — `POST /api/auth/admin/login`**
  RF: RF-1, RF-7, RF-8
  Hecho cuando: un request con credenciales válidas devuelve 200 y setea
  la cookie de sesión; con inválidas devuelve 401 con
  `intentos_restantes`; con cuenta bloqueada devuelve 423; con cuenta
  desactivada devuelve 403.

- [x] **T21 — `POST /api/auth/mesero/login`**
  RF: RF-1, RF-7, RF-9
  Hecho cuando: igual que T20 pero para mesero, y además invalida
  cualquier sesión previa de esa cuenta (RF-9).

- [x] **T22 — `POST /api/auth/logout`**
  RF: RF-9
  Hecho cuando: tras llamarlo, un request posterior con la misma cookie
  devuelve 401.

- [x] **T23 — `POST /api/auth/heartbeat` + middleware de inactividad**
  RF: RF-8
  Hecho cuando: sin heartbeat durante 31 minutos simulados, el siguiente
  request de admin devuelve 401; llamando heartbeat cada &lt;30 min, la
  sesión sigue viva indefinidamente.

- [x] **T24 — `GET /api/auth/session`**
  RF: RF-1 (soporte)
  Hecho cuando: devuelve `{id, username, role}` con sesión válida, y 401
  sin sesión.

- [x] **T25 — `POST /api/usuarios/meseros` (crear mesero)**
  RF: RF-2
  Hecho cuando: un admin autenticado crea un mesero con username+PIN
  válidos (201); un mesero autenticado recibe 403; un username duplicado
  devuelve 409.

- [x] **T26 — `POST /api/usuarios/meseros/{id}/reset-pin`**
  RF: RF-4
  Hecho cuando: tras la llamada, el PIN anterior ya no autentica y el
  nuevo sí; se cierra cualquier sesión activa de ese mesero.

- [x] **T27 — `POST .../desactivar` y `POST .../reactivar`**
  RF: RF-5
  Hecho cuando: desactivar un mesero sin mesas abiertas devuelve 200 y
  bloquea logins futuros; desactivar uno con mesas abiertas (mockeado)
  devuelve 409; reactivar revierte el estado.

- [x] **T28 — `POST .../desbloquear` (mesero)**
  RF: RF-3, RF-7
  Hecho cuando: requiere `nuevo_pin` en el body; sobre una cuenta no
  bloqueada devuelve 409; sobre una bloqueada, la desbloquea y dicho PIN
  queda activo para el siguiente login.

- [x] **T29 — `POST /api/usuarios/admins` (crear admin)**
  RF: RF-6, RF-10
  Hecho cuando: un admin autenticado crea otro admin con username+password
  válidos (201, complejidad validada); username duplicado devuelve 409.

- [x] **T30 — `POST /api/usuarios/admins/me/password`**
  RF: RF-6
  Hecho cuando: exige `password_actual` correcta y que
  `password_nueva == password_nueva_confirmacion`; rechaza (400) si
  cualquiera de las dos condiciones falla.

- [x] **T31 — Permiso `EsAdminSobrePropiaCuenta`**
  RF: RF-6
  Hecho cuando: un admin que intenta cualquier operación de escritura
  sobre **otra** cuenta admin (username, password, estado) recibe 403 en
  todos los endpoints de T29-T30.

---

## Fase 4 — Comandos de servidor (operador técnico)

- [x] **T32 — Comando `create_admin`**
  RF: RF-10
  Hecho cuando: con la base vacía, el comando crea el primer admin y
  `/admin` deja de estar bloqueado; correrlo de nuevo con un admin ya
  existente no rompe nada (según se decida: crea uno adicional o informa
  que ya hay admins).

- [x] **T33 — Comando `recover_admin_access`**
  RF: RF-7, RF-10
  Hecho cuando: sobre una cuenta admin bloqueada, la desbloquea de
  inmediato sin esperar los 20 min; sobre una con password olvidada, la
  resetea con la nueva provista.

- [x] **T34 — Comando `deactivate_admin`**
  RF: RF-10
  Hecho cuando: deja `is_active=False` sin borrar la fila; invalida
  cualquier sesión activa de esa cuenta; las filas de `AccionCuenta` que la
  referencian como `ejecutado_por` siguen intactas.

- [x] **T35 — Comando `rename_admin`**
  RF: RF-10
  Hecho cuando: cambia el username respetando el validador de T08; si el
  nuevo nombre ya existe (admin o mesero), el comando falla con un mensaje
  claro y no aplica el cambio; si la cuenta tenía sesión activa, queda
  invalidada.

---

## Fase 5 — Tests

- [x] **T36 — Unit tests de validadores**
  RF: RF-2, RF-6, RF-10
  Hecho cuando: `pytest`/`manage.py test` cubre los casos límite de T08 y
  T09 (username, PIN, password) y todos pasan.

- [x] **T37 — Unit tests de bloqueo y auto-desbloqueo**
  RF: RF-7
  Hecho cuando: cubren T12, T13 y T14 (bloqueo a los 5, reseteo tras
  éxito, auto-desbloqueo admin a los 20 min) y todos pasan.

- [x] **T38 — Unit tests de `garantizar_admin_activo`**
  RF: RF-6
  Hecho cuando: cubren el caso de único admin (rechaza) y de múltiples
  admins (permite), y todos pasan.

- [x] **T39 — Unit tests de mensajes RF-1**
  RF: RF-1
  Hecho cuando: las 5 combinaciones de T15 tienen un test cada una y
  todos pasan.

- [x] **T40 — Integration tests de login (admin + mesero)**
  RF: RF-1, RF-7
  Hecho cuando: T20 y T21 tienen un test por cada código de respuesta
  (200, 401, 403, 423) y todos pasan.

- [x] **T41 — Integration test: flujo bloqueo → desbloqueo → login**
  RF: RF-3, RF-4, RF-7, RF-11
  Hecho cuando: un test end-to-end reproduce 5 fallos → 423 → admin
  desbloquea con PIN nuevo → login exitoso con el PIN nuevo, y verifica
  las filas resultantes en `AccionCuenta`.

- [x] **T42 — Integration test: sesión única de mesero**
  RF: RF-9
  Hecho cuando: reproduce login en "dispositivo A", login en
  "dispositivo B", y confirma que un request con la cookie de A devuelve
  401.

- [x] **T43 — Integration test: inactividad de admin**
  RF: RF-8
  Hecho cuando: simula 31 minutos sin heartbeat y confirma 401 en el
  siguiente request; y por separado, confirma que heartbeats cada
  &lt;30 min mantienen la sesión viva.

- [x] **T44 — Integration test: aislamiento entre admins**
  RF: RF-6
  Hecho cuando: un admin autenticado intentando modificar username,
  password o estado de otro admin recibe 403 en cada endpoint relevante.

- [x] **T45 — Integration test: desactivar mesero con mesas abiertas**
  RF: RF-5
  Hecho cuando: con el mock de mesas abiertas activo, el endpoint de
  desactivar devuelve 409 con el detalle esperado.

- [x] **T46 — Integration test: trazabilidad por endpoint**
  RF: RF-11
  Hecho cuando: cada endpoint sensible de la Fase 3 tiene un test que
  verifica que se creó exactamente una fila nueva en `AccionCuenta` con
  los datos correctos.

- [x] **T47 — Tests de comandos CLI**
  RF: RF-10
  Hecho cuando: T32-T35 tienen al menos un test cada uno usando
  `call_command`, y todos pasan.

---

## Fase 6 — Frontend

- [x] **T48 — `proxy.ts` de protección de rutas** (renombrado de
  `middleware.ts`: Next.js 16 deprecó ese archivo en favor de `proxy.ts`)
  RF: RF-1
  Hecho cuando: acceder a una ruta de `/admin/(panel)/*` sin sesión admin
  redirige a `/admin/login`; ídem para `/mesero/(turno)/*` y sesión mesero.

- [x] **T49 — Página `/admin/login` + `LoginFormAdmin`**
  RF: RF-1
  Hecho cuando: la página solo renderiza el formulario de admin, envía a
  T20, y en éxito redirige al panel; en error muestra el mensaje que
  devuelve la API tal cual.

- [x] **T50 — Página `/mesero/login` + `LoginFormMesero` (PIN pad)**
  RF: RF-1
  Hecho cuando: la página solo renderiza el formulario de mesero con
  teclado numérico, envía a T21, y en éxito redirige a la PWA de turno.

- [x] **T51 — `lib/api/auth.ts`**
  RF: RF-1, RF-8, RF-9
  Hecho cuando: expone funciones `login`, `logout`, `session`,
  `heartbeat` que llaman a los endpoints correctos y propagan los errores
  tal cual los devuelve la API.

- [x] **T52 — `SessionHeartbeat.tsx`**
  RF: RF-8
  Hecho cuando: montado solo dentro de `/admin/(panel)`, dispara
  `heartbeat` ante `mousemove`/`click`/`keydown`/`scroll`/`touchstart`,
  limitado a 1 llamada por minuto.

- [x] **T53 — Pantalla de gestión de meseros**
  RF: RF-2, RF-3, RF-4, RF-5, RF-7
  Hecho cuando: desde el panel se puede crear, resetear PIN, activar,
  desactivar y desbloquear un mesero, cada acción llamando al endpoint
  correspondiente y reflejando su respuesta (incluidos los errores 409).

- [x] **T54 — Pantalla de gestión de admins**
  RF: RF-6, RF-10
  Hecho cuando: desde el panel se puede crear un admin adicional y
  cambiar la contraseña propia; no existe ningún botón para editar o
  desactivar a otro admin (esas acciones son solo CLI, RF-10).

- [x] **T55 — `lib/api/usuarios.ts`**
  RF: RF-2, RF-4, RF-5, RF-6, RF-7, RF-10
  Hecho cuando: expone una función por cada endpoint de gestión de la
  Fase 3 (meseros y admins), usada por T53 y T54.
