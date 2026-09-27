from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase

from apps.orders.routing import websocket_urlpatterns

User = get_user_model()

application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))


@database_sync_to_async
def _create_user(username, role, password="1234"):
    return User.objects.create_user(username=username, password=password, role=role)


@database_sync_to_async
def _session_cookie_for(user):
    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key


class OrderConsumerTests(TestCase):
    """T41 — /ws/pedidos/ is admin-only (plan.md, sección 4)."""

    async def test_connect_without_a_valid_session_is_rejected(self):
        communicator = WebsocketCommunicator(application, "/ws/pedidos/")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_connect_as_mesero_is_rejected(self):
        user = await _create_user("mesero_ws_orders", User.Role.MESERO)
        session_key = await _session_cookie_for(user)
        communicator = WebsocketCommunicator(
            application,
            "/ws/pedidos/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_connect_as_admin_is_accepted(self):
        user = await _create_user(
            "admin_ws_orders", User.Role.ADMIN, password="Sup3rSecreta"
        )
        session_key = await _session_cookie_for(user)
        communicator = WebsocketCommunicator(
            application,
            "/ws/pedidos/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_connected_admin_receives_group_messages(self):
        user = await _create_user(
            "admin_ws_orders2", User.Role.ADMIN, password="Sup3rSecreta"
        )
        session_key = await _session_cookie_for(user)
        communicator = WebsocketCommunicator(
            application,
            "/ws/pedidos/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "orders_admin", {"type": "pedidos.actualizado"}
        )
        response = await communicator.receive_json_from()
        self.assertEqual(response, {"type": "pedidos.actualizado"})

        await communicator.disconnect()
