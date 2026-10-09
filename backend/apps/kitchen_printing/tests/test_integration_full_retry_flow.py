from decimal import Decimal
from unittest.mock import patch

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase
from rest_framework.test import APIClient

from apps.kitchen_printing.adapters import PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.orders import services
from apps.orders.routing import websocket_urlpatterns

User = get_user_model()

application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))


def _patched_adapter(adapter):
    return patch(
        "apps.kitchen_printing.services.get_printer_adapter", return_value=adapter
    )


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


class FullFailureAndRetryFlowTests(TestCase):
    """T30 — end-to-end: send with the printer failing -> has_pending_print
    true -> retry succeeds via the HTTP endpoint -> has_pending_print
    false and the admin panel is notified in real time (RF-1, RF-8,
    RF-9, RF-10)."""

    async def test_full_flow(self):
        waiter = await _create_user("t30_w", User.Role.MESERO)
        await database_sync_to_async(services.resize_tables)(1)
        order = await database_sync_to_async(services.create_order)(waiter, 1)
        await database_sync_to_async(services.add_item)(
            order, None, "Limonada", Decimal("4.50")
        )

        client = APIClient()
        await database_sync_to_async(client.force_authenticate)(waiter)

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            response = await database_sync_to_async(client.post)(
                f"/api/pedidos/{order.id}/enviar"
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["print_warning"])

        mine = await database_sync_to_async(client.get)("/api/pedidos/mios")
        self.assertTrue(mine.data[0]["has_pending_print"])

        admin = await _create_user(
            "t30_admin", User.Role.ADMIN, password="Sup3rSecreta"
        )
        session_key = await _session_cookie_for(admin)
        communicator = WebsocketCommunicator(
            application,
            "/ws/pedidos/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        assert connected

        with _patched_adapter(FakePrinterAdapter()):
            retry_response = await database_sync_to_async(client.post)(
                f"/api/pedidos/{order.id}/reimprimir"
            )
        self.assertEqual(retry_response.status_code, 200)
        self.assertIsNone(retry_response.data["print_warning"])

        realtime = await communicator.receive_json_from(timeout=1)
        self.assertEqual(realtime, {"type": "pedidos.actualizado"})
        await communicator.disconnect()

        mine_after = await database_sync_to_async(client.get)("/api/pedidos/mios")
        self.assertFalse(mine_after.data[0]["has_pending_print"])
