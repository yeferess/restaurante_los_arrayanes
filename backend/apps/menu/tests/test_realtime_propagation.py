from decimal import Decimal

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase

from apps.menu import services
from apps.menu.routing import websocket_urlpatterns

User = get_user_model()

application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))


@database_sync_to_async
def _create_mesero():
    return User.objects.create_user(
        username="mesero_rt", password="1234", role=User.Role.MESERO
    )


@database_sync_to_async
def _session_cookie_for(user):
    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key


class RealTimeMenuPropagationTests(TestCase):
    """T25 — `notify_menu_changed()` reaches connected clients through the
    real channel layer (RF-6)."""

    async def _connected_communicator(self):
        user = await _create_mesero()
        session_key = await _session_cookie_for(user)
        communicator = WebsocketCommunicator(
            application,
            "/ws/menu/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        assert connected
        return communicator

    async def test_creating_a_category_does_not_notify_but_creating_a_product_does(
        self,
    ):
        communicator = await self._connected_communicator()

        category = await database_sync_to_async(services.create_category)("Bebidas")
        self.assertTrue(await communicator.receive_nothing(timeout=0.2))

        await database_sync_to_async(services.create_product)(
            name="Limonada", category_id=category.pk, price=Decimal("4.00")
        )
        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response, {"type": "menu.actualizado"})

        await communicator.disconnect()

    async def test_renaming_a_category_notifies(self):
        category = await database_sync_to_async(services.create_category)("Bebidas")
        communicator = await self._connected_communicator()

        await database_sync_to_async(services.rename_category)(category, "Refrescos")
        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response, {"type": "menu.actualizado"})

        await communicator.disconnect()

    async def test_deleting_an_empty_category_does_not_notify(self):
        category = await database_sync_to_async(services.create_category)("Bebidas")
        communicator = await self._connected_communicator()

        await database_sync_to_async(services.delete_category)(category)
        self.assertTrue(await communicator.receive_nothing(timeout=0.3))

        await communicator.disconnect()

    async def test_toggling_availability_notifies(self):
        category = await database_sync_to_async(services.create_category)("Bebidas")
        product = await database_sync_to_async(services.create_product)(
            name="Limonada", category_id=category.pk, price=Decimal("4.00")
        )
        communicator = await self._connected_communicator()

        await database_sync_to_async(services.set_product_availability)(
            product, is_available=False
        )
        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response, {"type": "menu.actualizado"})

        await communicator.disconnect()

    async def test_deleting_a_product_notifies(self):
        category = await database_sync_to_async(services.create_category)("Bebidas")
        product = await database_sync_to_async(services.create_product)(
            name="Limonada", category_id=category.pk, price=Decimal("4.00")
        )
        communicator = await self._connected_communicator()

        await database_sync_to_async(services.delete_product)(product)
        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response, {"type": "menu.actualizado"})

        await communicator.disconnect()
