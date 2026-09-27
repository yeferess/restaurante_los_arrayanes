from channels.generic.websocket import AsyncJsonWebsocketConsumer

ORDERS_GROUP_NAME = "orders_admin"


class OrderConsumer(AsyncJsonWebsocketConsumer):
    """/ws/pedidos/ (plan.md, sección 4): admin-only feed of order
    changes. Unlike MenuConsumer (002), meseros never connect here — they
    act on orders they already have on screen."""

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated or user.role != user.Role.ADMIN:
            await self.close()
            return
        await self.channel_layer.group_add(ORDERS_GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(ORDERS_GROUP_NAME, self.channel_name)

    async def pedidos_actualizado(self, event):
        await self.send_json({"type": "pedidos.actualizado"})
