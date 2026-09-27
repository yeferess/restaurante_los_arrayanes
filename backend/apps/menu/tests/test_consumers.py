from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase

from apps.menu.routing import websocket_urlpatterns

User = get_user_model()

application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))


@database_sync_to_async
def _create_mesero():
    return User.objects.create_user(
        username="mesero_ws", password="1234", role=User.Role.MESERO
    )


@database_sync_to_async
def _session_cookie_for(user):
    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key


class MenuConsumerTests(TestCase):
    """T23 — /ws/menu/ requires a valid session and joins the "menu"
    group (RF-6, RF-8)."""

    async def test_connect_without_a_valid_session_is_rejected(self):
        communicator = WebsocketCommunicator(application, "/ws/menu/")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_connect_with_a_valid_session_is_accepted(self):
        user = await _create_mesero()
        session_key = await _session_cookie_for(user)
        communicator = WebsocketCommunicator(
            application,
            "/ws/menu/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_connected_client_receives_messages_sent_to_the_menu_group(self):
        user = await _create_mesero()
        session_key = await _session_cookie_for(user)
        communicator = WebsocketCommunicator(
            application,
            "/ws/menu/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        channel_layer = get_channel_layer()
        await channel_layer.group_send("menu", {"type": "menu.actualizado"})
        response = await communicator.receive_json_from()
        self.assertEqual(response, {"type": "menu.actualizado"})

        await communicator.disconnect()
