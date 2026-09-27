# Constitución del Proyecto

1. **Stack mínimo**: Django (API REST + Channels) + Next.js + SQLite. No se añade Redis, Postgres, microservicios ni infraestructura extra sin reformar esta constitución.
2. **Offline-first en LAN**: ninguna función crítica (crear, cobrar, anular pedidos) depende de internet; el sistema opera 100% en la WiFi local del restaurante.
3. **Contrato de API**: frontends y backend solo se comunican vía API REST/WebSocket documentada; ningún frontend accede directo a la BD ni duplica lógica de negocio.
4. **Trazabilidad obligatoria**: toda anulación (de un ítem o de un pedido completo) y todo cambio de mesa registran quién, cuándo y por qué antes de ejecutarse; el cobro de un pedido y toda acción sensible sobre cuentas de usuario (crear, resetear PIN, activar, desactivar, desbloquear) registran quién y cuándo. Sin su registro correspondiente, se rechaza.
5. **Permisos por rol**: el mesero crea, edita, agrega ítems, anula ítems, corrige la mesa y envía los pedidos de sus propias mesas, y marca/desmarca su indicador de entregado; cualquier mesero puede liberar una mesa ya pagada, sin importar quién tomó el pedido; solo el admin anula un pedido completo, cobra, gestiona el número de mesas y gestiona usuarios/menú.
6. **Tests obligatorios**: toda acción sensible (regla 4) y todo endpoint de API tiene al menos un test automatizado antes de mergear.
7. **Idioma**: código (variables, funciones, clases, comentarios técnicos) en inglés; mensajes de commit en español.
