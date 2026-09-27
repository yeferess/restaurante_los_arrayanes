# 001 · Autenticación y gestión de usuarios — Plan técnico

Este plan traduce a diseño técnico (el "cómo") la especificación aprobada en
`spec.md` (el "qué/por qué"). No contiene código, solo estructura,
contratos, pseudocódigo y decisiones justificadas.

## Cumplimiento de `docs/constitution.md`

- **Regla 1 (stack mínimo)**: solo Django + DRF + Django Channels + Next.js
  + SQLite. Ninguna decisión de este plan introduce Redis, Postgres,
  microservicios ni colas de mensajes (ver sección 5, decisiones 1, 4 y 5).
- **Regla 2 (offline-first en LAN)**: autenticación por sesión de Django
  contra SQLite local; ningún endpoint llama a un servicio externo.
- **Regla 3 (contrato de API)**: Next.js nunca toca SQLite directamente;
  todo pasa por los endpoints REST de la sección 3.
- **Regla 4 (trazabilidad)**: modelo `AccionCuenta` (sección 2) registra
  quién y cuándo en toda acción sensible sobre cuentas (la constitución no
  exige "por qué" para gestión de usuarios, solo para pedidos).
- **Regla 5 (permisos por rol)**: permisos de DRF en cada endpoint
  (sección 3) separan estrictamente admin vs. mesero.
- **Regla 6 (tests obligatorios)**: sección 6 cubre el 100% de los
  endpoints y acciones sensibles.
- **Regla 7 (idioma)**: nombres de clases/campos/variables en inglés en el
  código real; este documento (como los demás `.md` del repo) permanece en
  español.

---

## 1. Estructura de módulos/archivos

### Backend (`/backend`)

```
backend/
  manage.py
  config/                      # proyecto Django
    settings.py
    urls.py                    # incluye accounts.urls bajo /api/
    asgi.py                    # Channels (no usado por este módulo, ya
                                # existe para otros módulos en tiempo real)
  apps/
    accounts/                  # app dedicada a este módulo (RF-1..RF-11)
      models.py                # Usuario, AccionCuenta, IntentoFallido
      serializers.py           # 1 serializer por endpoint de la sección 3
      permissions.py           # EsAdmin, EsMesero, EsAdminSobrePropiaCuenta
      services.py              # lógica de negocio pura (bloqueo, sesión
                                # única, garantía de admin activo) — sin
                                # dependencias de HTTP, para poder testear
                                # como unit tests (sección 6)
      views.py                 # 1 APIView/ViewSet por endpoint
      urls.py
      management/
        commands/
          crear_admin.py            # RF-10 (primer admin / operador técnico)
          recuperar_acceso_admin.py # RF-10 (password olvidada / desbloqueo)
          desactivar_admin.py       # RF-10 (desactivación permanente)
          renombrar_admin.py        # RF-10 (cambio de username admin)
      tests/
        test_models.py
        test_login_admin.py
        test_login_mesero.py
        test_gestion_meseros.py
        test_gestion_admins.py
        test_lockout.py
        test_sesiones.py
        test_commands.py
```

Cada archivo de `management/commands/` es la única superficie que puede
ejecutar las acciones que RF-10 restringe al operador técnico — no existe
ruta HTTP equivalente para ellas (ver sección 3).

### Frontend (`/frontend`, Next.js App Router)

```
frontend/
  middleware.ts                # RF-1: intercepta /admin/* y /mesero/*,
                                # valida sesión+rol contra la cookie antes
                                # de servir cualquier página protegida
  app/
    admin/
      login/page.tsx            # RF-1 — único formulario visible en /admin
      (panel)/
        layout.tsx               # exige sesión admin válida (RF-8)
        usuarios/
          meseros/page.tsx       # RF-2, RF-3, RF-4, RF-5, RF-7 (UI)
          admins/page.tsx        # RF-6, RF-10 (alta desde panel; las
                                  # acciones exclusivas de CLI se muestran
                                  # solo como texto informativo, no como
                                  # botones)
        cuenta/page.tsx          # RF-6 — cambiar la propia contraseña
    mesero/
      login/page.tsx             # RF-1 — único formulario visible en /mesero
      (turno)/
        layout.tsx                # exige sesión mesero válida (RF-9)
        ...                       # resto de la PWA, fuera de alcance
  lib/api/
    auth.ts                       # login/logout/heartbeat/session
    usuarios.ts                    # llamadas a los endpoints de gestión
  components/
    LoginFormAdmin.tsx
    LoginFormMesero.tsx            # teclado numérico tipo PIN pad
    SessionHeartbeat.tsx           # RF-8 — dispara el heartbeat en eventos
                                    # de actividad, solo se monta en /admin
    UsersTable.tsx
```

---

## 2. Modelo de datos

### Tabla `Usuario` (unifica admin y mesero — RF-2 exige unicidad global de
username entre ambos roles, un solo modelo lo resuelve sin tablas extra)

| Campo                  | Tipo                          | Restricciones                                                   | RF        |
|-------------------------|--------------------------------|------------------------------------------------------------------|-----------|
| `id`                    | `AutoField`                    | PK                                                                | —         |
| `username`              | `CharField(20)`                 | `unique=True` (case-insensitive), regex `^[a-z0-9_]{3,20}$`, se guarda normalizado en minúsculas | RF-2 |
| `role`                  | `CharField` choices `ADMIN`/`MESERO` | no editable tras creación                                    | RF-1, RF-5 |
| `password_hash`         | `CharField`                    | hash Django estándar (PBKDF2), nunca texto plano                | RF-2, RF-6, NFR cifrado |
| `is_active`             | `BooleanField` default `True`  | mesero: RF-5 (desactivada); admin: RF-10 (desactivación permanente, sin reactivación) | RF-5, RF-10 |
| `is_locked`             | `BooleanField` default `False` | bloqueo por intentos fallidos, distinto de `is_active` (RF-3)    | RF-7 |
| `locked_at`             | `DateTimeField` nullable       | usado para calcular los 20 min de auto-desbloqueo admin          | RF-7 |
| `failed_login_attempts` | `PositiveSmallIntegerField` default `0` | se resetea a 0 en login exitoso                        | RF-7 |
| `current_session_key`   | `CharField` nullable           | única sesión activa por mesero (RF-9); no se usa para admin      | RF-9 |
| `created_by`            | `ForeignKey('self', null=True, on_delete=PROTECT)` | quién creó esta cuenta                       | RF-2, RF-6, RF-11 |
| `created_at`            | `DateTimeField(auto_now_add=True)` | —                                                            | RF-2, RF-11 |

`on_delete=PROTECT` en `created_by`: ninguna cuenta se borra jamás (RF-5,
RF-10 son siempre desactivación, nunca `DELETE`), así que `PROTECT` nunca
debería dispararse en producción, pero documenta la garantía.

**Ejemplo de registro — admin:**

```json
{
  "id": 1,
  "username": "gerente_ana",
  "role": "ADMIN",
  "password_hash": "pbkdf2_sha256$...",
  "is_active": true,
  "is_locked": false,
  "locked_at": null,
  "failed_login_attempts": 0,
  "current_session_key": null,
  "created_by": null,
  "created_at": "2026-01-10T08:00:00Z"
}
```

**Ejemplo de registro — mesero:**

```json
{
  "id": 7,
  "username": "carlos_m",
  "role": "MESERO",
  "password_hash": "pbkdf2_sha256$...",
  "is_active": true,
  "is_locked": false,
  "locked_at": null,
  "failed_login_attempts": 2,
  "current_session_key": "8f3a...e21",
  "created_by": 1,
  "created_at": "2026-02-01T14:30:00Z"
}
```

### Tabla `AccionCuenta` (trazabilidad — RF-11, y las acciones sensibles de
RF-2/RF-4/RF-5/RF-6/RF-7/RF-10 que la constitución exige registrar)

| Campo           | Tipo                                             | RF |
|------------------|---------------------------------------------------|----|
| `id`             | `AutoField`                                        | — |
| `cuenta`         | `ForeignKey(Usuario, on_delete=PROTECT)`           | acción ejecutada sobre esta cuenta | RF-11 |
| `tipo_accion`    | `CharField` choices: `CREACION`, `RESET_PIN`, `ACTIVACION`, `DESACTIVACION`, `DESBLOQUEO`, `CAMBIO_PASSWORD_PROPIA`, `CREACION_ADMIN`, `DESACTIVACION_PERMANENTE_ADMIN`, `RENOMBRE_ADMIN`, `BLOQUEO_AUTOMATICO` | RF-2,4,5,6,7,10,11 |
| `ejecutado_por`  | `ForeignKey(Usuario, null=True, on_delete=PROTECT)`| quién la ejecutó; `null` si fue el operador técnico vía CLI | RF-11 |
| `via_cli`        | `BooleanField` default `False`                     | distingue acciones de panel vs. comando de servidor | RF-10 |
| `timestamp`      | `DateTimeField(auto_now_add=True)`                 | | RF-11 |

### Tabla `IntentoFallido` (soporte de RF-7, separada de `Usuario` para no
perder el historial cuando el contador se resetea)

| Campo       | Tipo                                       | RF |
|--------------|-----------------------------------------------|----|
| `id`         | `AutoField`                                    | — |
| `cuenta`     | `ForeignKey(Usuario, on_delete=CASCADE)`       | RF-7 |
| `timestamp`  | `DateTimeField(auto_now_add=True)`             | RF-7 |

No existe fila para intentos contra un `username` inexistente: el conteo
"simulado" que exige RF-1 se calcula sin persistir nada (ver pseudocódigo,
sección 4).

---

## 3. Contrato de la API

Todos los endpoints viven bajo `/api/`. Autenticación por cookie de sesión
`httpOnly` (ver decisión técnica 1). Todas las respuestas de error usan
`{"detail": "<mensaje>", "intentos_restantes"?: number}`.

| # | Endpoint | Método | RF | Auth | Request | Response 200/201 | Errores |
|---|-----------|--------|----|------|---------|---------------------|---------|
| 1 | `/api/auth/admin/login` | POST | RF-1, RF-7, RF-8 | pública | `{username, password}` | `{id, username, role}` + cookie | 401 credenciales (con `intentos_restantes`), 423 bloqueada, 403 desactivada permanente |
| 2 | `/api/auth/mesero/login` | POST | RF-1, RF-7, RF-9 | pública | `{username, pin}` | `{id, username, role}` + cookie | 401 credenciales, 423 bloqueada, 403 desactivada |
| 3 | `/api/auth/logout` | POST | RF-9 | sesión propia | — | 204 | 401 sin sesión |
| 4 | `/api/auth/heartbeat` | POST | RF-8 | admin | — | 200 `{expira_en_seg}` | 401 sin sesión / expirada |
| 5 | `/api/auth/session` | GET | RF-1 (soporte de `middleware.ts`) | sesión propia | — | `{id, username, role}` | 401 sin sesión |
| 6 | `/api/usuarios/meseros` | POST | RF-2 | admin | `{username, pin}` | 201 `{id, username, role, is_active, created_by, created_at}` | 400 formato inválido, 409 username duplicado |
| 7 | `/api/usuarios/meseros/{id}/reset-pin` | POST | RF-4 | admin | `{nuevo_pin}` | 200 | 400 formato, 404 no existe |
| 8 | `/api/usuarios/meseros/{id}/desactivar` | POST | RF-5 | admin | — | 200 | 409 mesas/pedidos abiertos, 404 |
| 9 | `/api/usuarios/meseros/{id}/reactivar` | POST | RF-5 | admin | — | 200 | 404, 409 ya activa |
| 10 | `/api/usuarios/meseros/{id}/desbloquear` | POST | RF-3, RF-7 | admin | `{nuevo_pin}` | 200 | 409 no está bloqueada, 400 formato de PIN |
| 11 | `/api/usuarios/admins` | POST | RF-6, RF-10 | admin | `{username, password}` | 201 | 400 complejidad de password / formato username, 409 username duplicado |
| 12 | `/api/usuarios/admins/me/password` | POST | RF-6 | admin (solo su propia cuenta) | `{password_actual, password_nueva, password_nueva_confirmacion}` | 200 | 400 password actual incorrecta, 400 no coincide confirmación, 400 complejidad |

**Fuera del contrato REST — comandos de servidor (RF-10):** creación del
primer admin, recuperación de acceso (password olvidada o desbloqueo
inmediato), desactivación permanente y renombrado de un admin **no tienen
endpoint HTTP**, por diseño explícito de RF-10 ("nunca desde el panel
web"). Se ejecutan como Django management commands (sección 1), operados
solo por quien tiene acceso a la terminal del servidor.

Códigos de estado usados y su porqué:
- **401** — sin sesión, sesión expirada (RF-8), o credenciales incorrectas.
- **423 Locked** — cuenta bloqueada por intentos fallidos (RF-7); se separa
  de 403 para que el frontend distinga el mensaje exacto de RF-1.
- **403** — cuenta desactivada (RF-5, RF-10), o acción no permitida por rol
  (RF-1 cruce de rol, RF-6 un admin tocando a otro admin).
- **404** — recurso no existe.
- **409** — conflictos de estado: username duplicado (RF-2), mesas abiertas
  (RF-5), dejaría cero admins activos (RF-6), o acción no aplica al estado
  actual (desbloquear algo que no está bloqueado, RF-7).

---

## 4. Pseudocódigo

### 4.1 Bloqueo por intentos fallidos (RF-1, RF-3, RF-7)

```
FUNCTION intentar_login(username_ingresado, credencial, rol_esperado):
    username = normalizar(username_ingresado)   # trim + lowercase, RF-2
    cuenta = Usuario.buscar(username, role=rol_esperado)

    SI cuenta NO existe:
        # RF-1: no revelar inexistencia — contador simulado, sin persistir nada
        intentos_simulados = hash_estable(username) % 5
        restantes = 5 - intentos_simulados
        RETORNAR 401("Usuario o contraseña incorrectos. "
                      "Te quedan {restantes} intentos antes del bloqueo.")

    SI cuenta.is_locked:
        SI cuenta.role == ADMIN Y ahora() - cuenta.locked_at >= 20_MINUTOS:
            cuenta.is_locked = False
            cuenta.locked_at = None
            cuenta.failed_login_attempts = 0
            guardar(cuenta)
            # sigue el flujo normal de verificación de credenciales debajo
        SINO SI cuenta.role == ADMIN:
            RETORNAR 423("Tu cuenta está bloqueada. Espera 20 minutos "
                          "o contacta al operador técnico del sistema.")
        SINO:  # mesero
            RETORNAR 423("Tu cuenta está bloqueada. Habla con un "
                          "administrador para resolverlo.")

    SI cuenta.is_active == False:
        SI cuenta.role == ADMIN:
            RETORNAR 403("Tu cuenta fue desactivada permanentemente. "
                          "Contacta al operador técnico si necesitas "
                          "una cuenta nueva.")
        SINO:
            RETORNAR 403("Tu cuenta está desactivada. Habla con un "
                          "administrador para resolverlo.")

    SI NO verificar_hash(credencial, cuenta.password_hash):
        cuenta.failed_login_attempts += 1
        registrar_intento_fallido(cuenta)                      # RF-7 traza
        SI cuenta.failed_login_attempts >= 5:
            cuenta.is_locked = True
            cuenta.locked_at = ahora()
            invalidar_todas_las_sesiones(cuenta)                # RF-7
            registrar_accion(cuenta, "BLOQUEO_AUTOMATICO", ejecutado_por=None)
            guardar(cuenta)
            RETORNAR 423(mensaje_bloqueo_segun_rol(cuenta.role))
        guardar(cuenta)
        restantes = 5 - cuenta.failed_login_attempts
        RETORNAR 401("Usuario o contraseña incorrectos. "
                      "Te quedan {restantes} intentos antes del bloqueo.")

    # --- login exitoso ---
    cuenta.failed_login_attempts = 0
    SI cuenta.role == MESERO:
        SI cuenta.current_session_key existe:
            invalidar_sesion(cuenta.current_session_key)        # RF-9
    nueva_sesion = crear_sesion(cuenta)
    cuenta.current_session_key = nueva_sesion.key
    guardar(cuenta)
    RETORNAR 200({id, username, role})
```

### 4.2 Desbloqueo manual de mesero — exige PIN nuevo en el mismo acto (RF-3, RF-7)

```
FUNCTION desbloquear_mesero(admin_actual, mesero_id, nuevo_pin):
    mesero = Usuario.buscar(id=mesero_id, role=MESERO)
    SI mesero.is_locked == False:
        RETORNAR 409("Esta cuenta no está bloqueada.")
    validar_formato_pin(nuevo_pin)                # 400 si falla, RF-2
    mesero.password_hash = hash(nuevo_pin)
    mesero.is_locked = False
    mesero.locked_at = None
    mesero.failed_login_attempts = 0
    guardar(mesero)
    registrar_accion(mesero, "DESBLOQUEO", ejecutado_por=admin_actual)  # RF-11
    RETORNAR 200()
```

### 4.3 Control de inactividad y heartbeat de admin (RF-8)

```
# Middleware backend, se ejecuta en cada request autenticado
MIDDLEWARE verificar_inactividad(request):
    SI request.usuario NO existe O request.usuario.role != ADMIN:
        CONTINUAR
    ultima_actividad = request.session['ultima_actividad']
    SI ahora() - ultima_actividad > 30_MINUTOS:
        cerrar_sesion(request)
        RETORNAR 401("Sesión expirada por inactividad.")
    CONTINUAR

ENDPOINT POST /api/auth/heartbeat:
    SI request.usuario NO autenticado:
        RETORNAR 401
    request.session['ultima_actividad'] = ahora()
    guardar_sesion(request.session)
    RETORNAR 200({expira_en_seg: 1800})
```

```
# Frontend (Next.js), componente SessionHeartbeat.tsx — solo se monta
# dentro de /admin/(panel). Detalle de implementación, no forma parte
# del contrato de API (RF-8 solo exige "actividad ⇒ no expira").
ultimo_envio = 0
ON evento(mousemove | click | keydown | scroll | touchstart):
    SI ahora() - ultimo_envio >= 60_SEGUNDOS:
        POST /api/auth/heartbeat
        ultimo_envio = ahora()
```

---

## 5. Decisiones técnicas justificadas

1. **Sesión de Django (cookie `httpOnly`) en vez de JWT.**
   Descartado: JWT de acceso/refresco. Revocar un JWT antes de su
   expiración (necesario para RF-7 y RF-9) exige una blacklist, típicamente
   en Redis — viola la regla 1 de la constitución. Las sesiones de Django
   ya viven en SQLite y se invalidan borrando una fila, sin infraestructura
   nueva.

2. **Un solo modelo `Usuario` con campo `role`, en vez de modelos
   `Admin`/`Mesero` separados.**
   Descartado: dos tablas independientes. RF-2 exige unicidad de username
   *global* entre ambos roles; con tablas separadas esa validación
   necesitaría una tabla extra de "usernames reservados", duplicando
   lógica. Un `UniqueConstraint` en una sola tabla lo resuelve nativamente.

3. **Mismo hasher de Django (PBKDF2) para PIN de mesero y contraseña de
   admin.**
   Descartado: un hash más liviano (ej. SHA-256 con salt manual) para el
   PIN, asumiendo que "es corto, no necesita tanto costo". Un hash sin
   key-stretching es más vulnerable a fuerza bruta offline si la base de
   datos se filtra, y el costo extra de PBKDF2 es irrelevante en un sistema
   con pocos logins por minuto. Reutilizar el hasher estándar evita
   mantener dos implementaciones criptográficas.

4. **Contador de intentos (`failed_login_attempts`, `is_locked`,
   `locked_at`) en el propio modelo `Usuario`, en vez de calcular el
   bloqueo contando filas de una tabla de intentos.**
   Descartado: derivar el estado de bloqueo dinámicamente contando
   `IntentoFallido` recientes en cada login. Añadiría una consulta extra en
   el camino crítico de autenticación sin beneficio real a esta escala; el
   contador desnormalizado es trivial de mantener porque solo el propio
   request de login lo modifica.

5. **Desbloqueo automático de admin a los 20 min: verificación perezosa en
   el login, no un job periódico.**
   Descartado: tarea programada (Celery beat o cron del SO) que recorra
   cuentas bloqueadas cada minuto. Celery requiere un broker (Redis),
   prohibido por la regla 1; un cron de sistema operativo es
   infraestructura fuera del stack declarado. Nadie necesita que la cuenta
   "aparezca desbloqueada" mientras nadie intenta usarla — basta resolverlo
   en el momento del intento de login (pseudocódigo 4.1).

6. **Invalidar la sesión anterior del mesero en vez de rechazar el nuevo
   login (RF-9).**
   Descartado: bloquear el login en el segundo dispositivo mientras el
   primero siga activo. Es más probable que el mesero haya cambiado de
   tablet por una razón operativa (batería, dispositivo compartido) que un
   intento malicioso; rechazar el nuevo login generaría más fricción
   operativa que el riesgo real que evitaría (decisión ya tomada en la
   spec, RF-9).

7. **Protección de rutas con `middleware.ts` de Next.js, en vez de
   verificación solo en cliente (`useEffect`).**
   Descartado: validar sesión únicamente del lado del cliente tras montar
   la página. Eso deja una ventana donde el HTML/JS de una pantalla
   protegida ya se descargó antes de redirigir, y no cumple bien RF-1
   ("mostrar únicamente el formulario correspondiente") desde el primer
   byte. El middleware corre antes de renderizar.

8. **Acciones exclusivas del operador técnico (RF-10) como Django
   management commands, no scripts sueltos.**
   Descartado: scripts Python independientes que se conectan directo a
   SQLite. Duplicarían validaciones (unicidad, hashing, formato) que ya
   viven en los modelos/serializers, arriesgando que ambos caminos
   diverjan. Los management commands reutilizan el mismo ORM y las mismas
   validaciones que la API, sin infraestructura adicional.

---

## 6. Estrategia de tests

Cumpliendo la regla 6 de la constitución (toda acción sensible y todo
endpoint tiene al menos un test).

### Unitarios (`Django TestCase`, sin HTTP — prueban `services.py` y
`models.py` en aislamiento)

- Validación de formato de `username` (3-20 caracteres, regex, unicidad
  case-insensitive global) — RF-2.
- Validación de formato de PIN (4-6 dígitos) y de password admin (8+,
  letras+números) — RF-2, RF-6, RF-10.
- Lógica de bloqueo: acumulación hasta 5, reseteo tras éxito, cálculo de
  los 20 minutos de auto-desbloqueo de admin — RF-7.
- Lógica de "al menos un admin activo": rechazo si una acción dejaría cero
  admins — RF-6.
- Mapeo estado→mensaje de RF-1 (bloqueada/desactivada × admin/mesero) —
  RF-1.
- Hashing: `set_password`/`check_password` funcionan igual para PIN y
  contraseña — NFR de cifrado.

### Integración (`DRF APIClient`, HTTP real contra la API)

- Los 12 endpoints de la sección 3: status code y payload correctos para
  cada caso de éxito y de error (400/401/403/404/409/423) — cubre RF-1 a
  RF-11 uno a uno.
- Flujo completo: mesero falla PIN 5 veces → bloqueo (RF-7) → admin
  desbloquea con PIN nuevo (RF-3, RF-4) → mesero entra con el PIN nuevo, no
  con el anterior — RF-3, RF-4, RF-7.
- RF-9: login en "dispositivo A", login en "dispositivo B" → la cookie de
  A deja de funcionar en un request posterior.
- RF-8: login de admin, se avanza el reloj simulado +31 min sin heartbeat →
  el siguiente request exige login de nuevo.
- RF-6: un admin autenticado intenta modificar username/password/estado de
  otro admin vía API → 403 en todos los endpoints relevantes.
- RF-5: desactivar un mesero con mesas abiertas (mockeando la dependencia
  del módulo de pedidos) → 409.
- RF-11: cada endpoint sensible deja exactamente una fila nueva en
  `AccionCuenta` con el admin ejecutor y el tipo de acción correctos.
- RF-6 (último admin): intentar la única acción que podría dejar el
  sistema sin admins activos → 409.

### Comandos CLI (`call_command`, sin HTTP)

- `crear_admin`: primer admin cuando no existe ninguno; rechazo si ya
  existe uno y se pide de nuevo el flujo de "primer admin".
- `recuperar_acceso_admin`: resetea contraseña y/o desbloquea de inmediato,
  sin esperar los 20 minutos — RF-7, RF-10.
- `desactivar_admin`: soft-delete (nunca borra fila), invalida sesión
  activa, preserva referencias de `AccionCuenta` — RF-10.
- `renombrar_admin`: valida unicidad y formato igual que el panel; rechaza
  duplicados — RF-10.

### Frontend (fuera del alcance estricto de la regla 6, recomendado)

- Componente de login: `/admin` solo renderiza `LoginFormAdmin`, `/mesero`
  solo `LoginFormMesero` — RF-1.

---

## Cobertura de requisitos funcionales

| RF | Cubierto en |
|----|--------------|
| RF-1 | Sección 3 (endpoints 1-2, códigos de error), Sección 4.1, Sección 1 (`middleware.ts`) |
| RF-2 | Sección 2 (`Usuario`), Sección 3 (endpoint 6) |
| RF-3 | Sección 3 (endpoint 10), Sección 4.2 |
| RF-4 | Sección 3 (endpoint 7), Sección 4.2 |
| RF-5 | Sección 3 (endpoints 8-9) |
| RF-6 | Sección 2 (`Usuario`), Sección 3 (endpoints 11-12), Decisión técnica 2 |
| RF-7 | Sección 2 (`IntentoFallido`), Sección 4.1, Decisión técnica 4 y 5 |
| RF-8 | Sección 3 (endpoint 4), Sección 4.3 |
| RF-9 | Sección 2 (`current_session_key`), Sección 4.1, Decisión técnica 6 |
| RF-10 | Sección 1 (management commands), Sección 3 ("fuera del contrato REST") |
| RF-11 | Sección 2 (`AccionCuenta`), todas las funciones de servicio en sección 4 que llaman `registrar_accion` |
