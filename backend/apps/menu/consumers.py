from channels.generic.websocket import AsyncJsonWebsocketConsumer

MENU_GROUP_NAME = "menu"


class MenuConsumer(AsyncJsonWebsocketConsumer):
    """/ws/menu/ (RF-6, RF-8): broadcasts menu changes to connected apps.

    A single shared group for every connected client (admin or mesero) —
    the menu is identical for all of them, so there's nothing to filter
    by recipient (see plan.md, decision 6).
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(MENU_GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(MENU_GROUP_NAME, self.channel_name)

    async def menu_actualizado(self, event):
        await self.send_json({"type": "menu.actualizado"})
