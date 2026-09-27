# 002 · Gestión del menú (catálogo de productos) — Plan técnico

Este plan traduce a diseño técnico (el "cómo") la especificación aprobada
en `spec.md` (el "qué/por qué"). No contiene código, solo estructura,
contratos, pseudocódigo y decisiones justificadas.

> **Nota de alcance**: a diferencia de un borrador inicial de este plan,
> `Producto` **no** tiene un campo `activo`/inactivo. La spec (RF-5) exige
> eliminación definitiva sin estado intermedio — el admin nunca "desactiva"
> un producto para borrarlo después, solo lo elimina o lo recrea si lo
> necesita de nuevo. El único estado intermedio que existe es
> `disponible` (RF-4), que es un concepto distinto (oferta del día, no
> ciclo de vida del producto).

## Cumplimiento de `docs/constitution.md`

- **Regla 1 (stack mínimo)**: solo Django + DRF + Django Channels +
  Next.js + SQLite. Ninguna decisión de este plan introduce Redis,
  Postgres, colas de mensajes ni jobs programados (sección 5).
- **Regla 2 (offline-first en LAN)**: lectura/escritura de menú y
  propagación en tiempo real corren sobre Channels + SQLite locales;
  ningún endpoint depende de un servicio externo.
- **Regla 3 (contrato de API)**: Next.js nunca toca SQLite directamente;
  todo pasa por los endpoints REST (sección 3) y el canal WebSocket
  (sección 4).
- **Regla 4 (trazabilidad)**: no aplica — la constitución solo exige
  trazabilidad para pedidos y cuentas de usuario, no para el catálogo de
  menú (confirmado en `spec.md`, "Dudas abiertas"). Ningún modelo de este
  plan registra quién/cuándo.
- **Regla 5 (permisos por rol)**: "solo el admin... gestiona
  usuarios/menú" — todos los endpoints de escritura de la sección 3
  exigen rol admin; el mesero solo tiene acceso de lectura (RF-7, RF-8).
- **Regla 6 (tests obligatorios)**: sección 6 cubre el 100% de los
  endpoints y del canal en tiempo real.
- **Regla 7 (idioma)**: nombres de clases/campos/variables en inglés en
  el código real (`Category`, `Product`, `is_available`, etc.); este
  documento permanece en español.

---

## 1. Estructura de módulos/archivos

### Backend (`/backend`)

```
backend/
  config/
    asgi.py                    # ya existe (módulo 001); se agrega
                                # menu.routing al ProtocolTypeRouter
  apps/
    menu/                      # app dedicada a este módulo (RF-1..RF-8)
      models.py                # Category, Product
      serializers.py           # 1 serializer por endpoint de la sección 3
      permissions.py           # reutiliza IsAdmin/IsMesero de
                                # apps.accounts.permissions (decisión 7)
      services.py               # lógica de negocio pura: unicidad,
                                # validación de categoría, disparo de
                                # notificación en tiempo real — sin
                                # dependencias de HTTP (testeable como
                                # unit test, sección 6)
      views.py                 # 1 APIView/ViewSet por endpoint
      urls.py                  # incluido en config/urls.py bajo /api/
      consumers.py              # MenuConsumer (Channels) — RF-6
      routing.py                 # websocket_urlpatterns: /ws/menu/
      tests/
        test_models.py
        test_categorias.py
        test_productos_crear.py
        test_productos_editar.py
        test_productos_disponibilidad.py
        test_productos_eliminar.py
        test_menu_lectura.py
        test_permisos.py
        test_consumers.py
```

### Frontend (`/frontend`, Next.js App Router)

```
frontend/
  app/
    admin/(panel)/
      menu/
        categorias/page.tsx    # RF-1 (UI: crear, renombrar, eliminar)
        productos/page.tsx     # RF-2, RF-3, RF-4, RF-5 (UI)
    mesero/(turno)/
      menu/page.tsx             # RF-7 (lectura) + botón "Actualizar
                                 # menú" (RF-6) + suscripción al socket
  lib/api/
    menu.ts                     # llamadas REST de la sección 3
    menuSocket.ts                # conexión a /ws/menu/, reconexión con
                                 # backoff, dispara refetch al recibir
                                 # un evento (ver sección 4)
  components/
    CategoriasManagement.tsx
    ProductosManagement.tsx      # incluye el selector de categoría como
                                  # lista desplegable (RF-2, nunca texto
                                  # libre)
    MenuMeseroView.tsx
    RefrescarMenuButton.tsx      # RF-6 — mismo refetch que usa el socket
```

---

## 2. Modelo de datos

### Tabla `Category`

| Campo                | Tipo                          | Restricciones                                                        | RF   |
|-----------------------|--------------------------------|-------------------------------------------------------------------------|------|
| `id`                  | `AutoField`                    | PK                                                                       | —    |
| `name`                | `CharField(50)`                | no vacío, preserva la capitalización ingresada                          | RF-1 |
| `normalized_name`     | `CharField(50)`                | `unique=True`; se recalcula a `name.lower()` en cada `save()`, nunca se expone en la API | RF-1 |

`normalized_name` es lo que hace atómica (a nivel de base de datos) la
regla "nombre único ignorando mayúsculas/minúsculas" incluso bajo
creación concurrente (ver decisión técnica 1) — `name` se conserva tal
cual lo escribió el admin para mostrarlo bonito en la UI del mesero.

**Ejemplo de registro:**

```json
{
  "id": 1,
  "name": "Bebidas",
  "normalized_name": "bebidas"
}
```

### Tabla `Product`

| Campo                | Tipo                                              | Restricciones                                                    | RF        |
|-----------------------|-----------------------------------------------------|---------------------------------------------------------------------|-----------|
| `id`                  | `AutoField`                                          | PK                                                                   | —         |
| `name`                | `CharField(100)`                                     | no vacío, preserva capitalización                                    | RF-2, RF-3|
| `normalized_name`     | `CharField(100)`                                     | `unique=True`, análogo a `Category.normalized_name`                  | RF-2, RF-3|
| `category`            | `ForeignKey(Category, on_delete=PROTECT)`            | debe existir; `PROTECT` refuerza a nivel de BD la regla de RF-1      | RF-1, RF-2, RF-3 |
| `price`               | `DecimalField(max_digits=10, decimal_places=2)`      | `> 0`                                                                 | RF-2, NFR precisión monetaria |
| `is_available`        | `BooleanField` default `True`                        | oculta el producto de la lectura del mesero cuando es `False`        | RF-4, RF-7 |

No existe columna `activo`/soft-delete (ver nota de alcance al inicio):
eliminar un `Product` es un `DELETE` real de la fila (RF-5). Ningún
modelo de este módulo ni del futuro módulo de pedidos referencia
`Product` con una FK — las líneas de pedido guardarán su propia copia de
`name` y `price` en el momento de agregarse (RF-5, RF-3), así que borrar
un producto nunca falla por restricción de integridad referencial.

**Ejemplo de registro:**

```json
{
  "id": 12,
  "name": "Limonada natural",
  "normalized_name": "limonada natural",
  "category_id": 1,
  "price": "4.50",
  "is_available": true
}
```

---

## 3. Contrato de la API

Todos los endpoints viven bajo `/api/menu/`. Autenticación por cookie de
sesión (heredada del módulo 001). Todas las respuestas de error usan
`{"detail": "<mensaje>"}`.

| # | Endpoint | Método | RF | Auth | Request | Response 200/201/204 | Errores |
|---|-----------|--------|----|------|---------|------------------------|---------|
| 1 | `/api/menu/categorias` | GET | RF-1, RF-2 (soporta el selector) | admin | — | `[{id, name}]` | 401, 403 |
| 2 | `/api/menu/categorias` | POST | RF-1 | admin | `{name}` | 201 `{id, name}` | 400 nombre vacío/>50 car., 409 nombre duplicado |
| 3 | `/api/menu/categorias/{id}` | PATCH | RF-1 | admin | `{name}` | 200 `{id, name}` | 400, 404, 409 nombre duplicado |
| 4 | `/api/menu/categorias/{id}` | DELETE | RF-1 | admin | — | 204 | 404, 409 tiene productos asignados |
| 5 | `/api/menu/productos` | GET | RF-2..RF-5 (gestión) | admin | — | `[{id, name, category, price, is_available}]` (incluye no disponibles) | 401, 403 |
| 6 | `/api/menu/productos` | POST | RF-2 | admin | `{name, category_id, price, is_available?}` | 201 (mismo shape que #5) | 400 nombre vacío/>100 car., precio ≤0/no numérico, `category_id` inválido o inexistente; 409 nombre duplicado |
| 7 | `/api/menu/productos/{id}` | PATCH | RF-3 | admin | `{name?, category_id?, price?}` | 200 | 400, 404, 409 nombre duplicado |
| 8 | `/api/menu/productos/{id}/disponibilidad` | POST | RF-4 | admin | `{is_available}` | 200 | 400 campo faltante, 404 |
| 9 | `/api/menu/productos/{id}` | DELETE | RF-5 | admin | — | 204 | 404 |
| 10 | `/api/menu` | GET | RF-7 | admin o mesero | — | `[{id, name, category, price}]` — **solo** `is_available=True` | 401 |

Endpoint #10 es la única lectura expuesta al mesero; los endpoints #1 y #5
(listas completas, incluidos no disponibles) son exclusivos de admin
porque alimentan las pantallas de gestión, no la PWA de mesero (ver
decisión técnica 8).

Códigos de estado usados y su porqué:
- **401** — sin sesión (RF-8).
- **403** — sesión válida pero de rol mesero intentando un endpoint de
  escritura o una lista de gestión (#1, #5) (RF-7, RF-8).
- **404** — categoría o producto no existe.
- **409** — nombre duplicado (categoría o producto, RF-1/RF-2/RF-3), o
  intento de eliminar una categoría con al menos un producto asignado
  (RF-1).

---

## 4. Mecanismo de propagación en tiempo real

### Canal

- `apps/menu/consumers.py` define `MenuConsumer(AsyncJsonWebsocketConsumer)`
  en `/ws/menu/`. Al conectar, valida la sesión Django (mismo middleware
  ASGI de autenticación que ya requiere el stack para Channels) y exige
  rol `MESERO` o `ADMIN`; sin sesión válida se rechaza la conexión
  (RF-8 aplicado también al canal en tiempo real).
- Todos los clientes conectados se unen a un único grupo de Channels,
  `"menu"` — no hay partición por mesa ni por usuario, porque el menú es
  igual para todos los meseros (decisión técnica 6).

### Disparo del evento (RF-6)

`services.py` centraliza cada escritura (crear/editar/cambiar
disponibilidad/eliminar producto, renombrar categoría) y, tras guardar en
la base de datos, llama a `channel_layer.group_send("menu", {...})` con
un evento "dumb" de invalidación:

```json
{ "type": "menu.actualizado" }
```

Crear o eliminar una categoría **sin productos asignados** no pasa por
este disparo (caso límite explícito de RF-6): esas dos operaciones viven
en un camino de código separado que nunca llama a
`notificar_cambio_de_menu()`.

### Reacción del cliente

- `menuSocket.ts` abre el WebSocket al montar la vista de menú del
  mesero, con reconexión automática (backoff exponencial simple).
- Al recibir `menu.actualizado`, ejecuta el mismo `fetch` que usa el
  botón manual: `GET /api/menu` y reemplaza el estado local completo.
- El botón **"Actualizar menú"** (RF-6) llama exactamente a esa misma
  función de refetch, sin depender de si el socket está conectado — así
  funciona igual si el WebSocket nunca llegó a conectar, se cayó, o el
  evento se perdió en el camino.

### Pseudocódigo

```
FUNCTION notificar_cambio_de_menu():
    channel_layer.group_send("menu", {"type": "menu.actualizado"})

FUNCTION eliminar_producto(producto_id):
    producto = Product.buscar(id=producto_id)
    producto.eliminar()                       # RF-5
    notificar_cambio_de_menu()                # RF-6
    RETORNAR 204

FUNCTION eliminar_categoria(categoria_id):
    categoria = Category.buscar(id=categoria_id)
    SI Product.objects.filter(category=categoria).existe():
        RETORNAR 409("Reasigna los productos de esta categoría antes de eliminarla.")
    categoria.eliminar()
    # sin notificar_cambio_de_menu(): no hay nada visible que cambie (RF-6)
    RETORNAR 204
```

---

## 5. Decisiones técnicas justificadas

1. **Campo espejo `normalized_name` (lowercase, `unique=True` en BD) en
   vez de forzar siempre minúsculas en el campo visible `name`.**
   Descartado: normalizar `name` a minúsculas al guardar, como se hizo
   con `username` en el módulo 001. Ahí no importa la presentación porque
   el username nunca se muestra "bonito"; el nombre de categoría/producto
   sí se muestra al mesero, así que forzarlo a minúsculas degradaría la
   UI. El campo espejo logra unicidad atómica sin sacrificar la
   presentación.

2. **`Product.category` con `on_delete=PROTECT`.**
   Descartado: `on_delete=CASCADE`, que borraría productos en cascada al
   eliminar su categoría — viola directamente RF-1 (eliminar una
   categoría con productos asignados debe rechazarse, nunca arrastrar
   productos). `PROTECT` refuerza a nivel de base de datos la misma regla
   que ya valida la vista, como red de seguridad ante un futuro bug.

3. **Ninguna FK desde el futuro modelo de líneas de pedido hacia
   `Product`; ese módulo copiará `name` y `price` al agregar la línea.**
   Descartado: FK con `on_delete=PROTECT` en la línea de pedido, que
   impediría para siempre eliminar un producto que alguna vez se pidió —
   contradice directamente RF-5 (eliminación sin restricciones de
   historial).

4. **`price` como `DecimalField(max_digits=10, decimal_places=2)`, no
   `FloatField`.**
   Descartado: `FloatField`, que introduce errores de redondeo binario en
   aritmética monetaria — viola el NFR de precisión monetaria de la spec.

5. **Notificación en tiempo real "dumb" (evento de invalidación sin
   payload) que dispara un refetch completo de `GET /api/menu`,
   reutilizado también por el botón manual.**
   Descartado: enviar por el socket el objeto modificado (diff) y
   mergearlo en el estado del cliente. Mantener eso consistente exige
   resolver orden de llegada, reconexión con eventos perdidos y merges
   parciales — complejidad innecesaria para un catálogo que cabe entero
   en una sola respuesta HTTP.

6. **Un único grupo de Channels (`"menu"`) para todos los clientes
   conectados, sin partición por mesa ni por usuario.**
   Descartado: un grupo por mesero o por sesión. El menú es idéntico para
   todos los meseros — no hay ningún destinatario que deba filtrarse (a
   diferencia del futuro módulo de pedidos, donde sí importará quién ve
   qué mesa).

7. **Reutilizar `IsAdmin`/`IsMesero` de `apps.accounts.permissions`
   (módulo 001) en vez de duplicar clases de permisos en `apps.menu`.**
   Descartado: redefinir permisos propios en la nueva app — duplicaría
   lógica de rol ya probada, arriesgando que ambas definiciones diverjan
   con el tiempo.

8. **Endpoints de lectura separados: `GET /api/menu/productos` (admin,
   incluye no disponibles) vs. `GET /api/menu` (mesero, solo
   disponibles).**
   Descartado: un único endpoint con un parámetro `?incluir_no_disponibles=true`
   protegido por rol. Es funcionalmente equivalente, pero mezcla en una
   sola ruta la superficie de "gestión" (admin) con la de "consulta"
   (mesero), dificultando razonar sobre permisos y cacheo por separado.

---

## 6. Estrategia de tests

Cumpliendo la regla 6 de la constitución (todo endpoint de API tiene al
menos un test).

### Unitarios (`Django TestCase`, sin HTTP — prueban `services.py` y
`models.py` en aislamiento)

- Unicidad case-insensitive de nombre de categoría y de producto vía
  `normalized_name` — RF-1, RF-2, RF-3.
- Validaciones de campo: nombre vacío/demasiado largo, precio ≤0 o no
  numérico — RF-1, RF-2.
- Regla de servicio "no eliminar categoría con al menos un producto
  asignado" — RF-1.
- `notificar_cambio_de_menu()` se llama en crear/editar/disponibilidad/
  eliminar producto y en renombrar categoría, y **no** se llama en
  crear/eliminar una categoría vacía — RF-6.

### Integración (`DRF APIClient`, HTTP real)

- Los 10 endpoints de la sección 3: status code y payload correctos para
  cada caso de éxito y de error (400/401/403/404/409) — cubre RF-1 a
  RF-8 uno a uno.
- Flujo completo: crear categoría → crear producto en ella → intentar
  eliminar la categoría (409) → eliminar el producto → eliminar la
  categoría (204) — RF-1, RF-2, RF-5.
- `GET /api/menu` (mesero) nunca incluye productos con
  `is_available=False`, aunque `GET /api/menu/productos` (admin) sí los
  liste — RF-4, RF-7.
- RF-8: un mesero autenticado recibe 403 en cada uno de los endpoints de
  escritura y en las listas de gestión (#1, #5); una request sin sesión
  recibe 401 en cualquier endpoint del módulo.
- RF-5: eliminar un producto no falla ni afecta un "pedido" simulado que
  ya lo referenciaba (mock del módulo de pedidos, mismo patrón que el
  módulo 001 mockeó `has_open_tables`).

### Canal en tiempo real (`channels.testing.WebsocketCommunicator`)

- Un cliente mesero conectado recibe `menu.actualizado` cuando el admin
  crea, edita, cambia disponibilidad o elimina un producto, o renombra
  una categoría — RF-6.
- Un cliente mesero conectado **no** recibe ningún evento cuando el admin
  crea o elimina una categoría sin productos asignados — RF-6 (caso
  límite).
- Un intento de conexión sin sesión válida es rechazado por el consumer —
  RF-8 aplicado al canal.

### Frontend (fuera del alcance estricto de la regla 6, recomendado)

- El botón "Actualizar menú" y la llegada de un evento por socket llaman
  a la misma función de refetch y producen el mismo resultado en pantalla
  — RF-6.

---

## Cobertura de requisitos funcionales

| RF | Cubierto en |
|----|--------------|
| RF-1 | Sección 2 (`Category`), Sección 3 (endpoints 1-4), Sección 4 (pseudocódigo `eliminar_categoria`), Decisión técnica 1 y 2 |
| RF-2 | Sección 2 (`Product`), Sección 3 (endpoint 6), Decisión técnica 1 y 4 |
| RF-3 | Sección 2 (`Product`), Sección 3 (endpoint 7), Decisión técnica 1 |
| RF-4 | Sección 2 (`is_available`), Sección 3 (endpoint 8), Sección 3 (endpoint 10, filtro) |
| RF-5 | Sección 2 (sin FK viva ni `activo`), Sección 3 (endpoint 9), Decisión técnica 3 |
| RF-6 | Sección 4 completa, Decisión técnica 5 y 6, pseudocódigo |
| RF-7 | Sección 3 (endpoint 10), Sección 2 (filtro `is_available`) |
| RF-8 | Sección 1 (`permissions.py`), Sección 3 (columna Auth y códigos 401/403), Sección 4 (auth del consumer), Decisión técnica 7 |
