from channels.db import database_sync_to_async
from channels.testing import HttpCommunicator, WebsocketCommunicator
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase

from config.asgi import application

User = get_user_model()


@database_sync_to_async
def _create_mesero():
    return User.objects.create_user(
        username="mesero_asgi", password="1234", role=User.Role.MESERO
    )


@database_sync_to_async
def _session_cookie_for(user):
    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key


class AsgiRoutingTests(TestCase):
    """T24 — the project's ProtocolTypeRouter serves HTTP and the menu
    WebSocket route without breaking either (RF-6 infrastructure)."""

    async def test_http_requests_still_work(self):
        communicator = HttpCommunicator(
            application,
            "GET",
            "/api/auth/session",
            headers=[(b"host", b"testserver")],
        )
        response = await communicator.get_response()
        self.assertEqual(response["status"], 401)

    async def test_websocket_menu_route_resolves_through_the_project_router(self):
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
