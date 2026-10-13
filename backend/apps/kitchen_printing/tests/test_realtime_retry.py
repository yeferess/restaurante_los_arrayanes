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

from apps.kitchen_printing import services as kitchen_services
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


class RetryPrintRealtimeTests(TestCase):
    """T26 — every print attempt ("Imprimir pedido", RF-1) notifies
    connected admins through the existing real-time channel, so the
    "No impreso en cocina" mark appears or clears right away (RF-10)."""

    async def _connected_admin_communicator(self):
        admin = await _create_user(
            "admin_rt_print", User.Role.ADMIN, password="Sup3rSecreta"
        )
        session_key = await _session_cookie_for(admin)
        communicator = WebsocketCommunicator(
            application,
            "/ws/pedidos/",
            headers=[(b"cookie", f"sessionid={session_key}".encode())],
        )
        connected, _ = await communicator.connect()
        assert connected
        return communicator

    async def test_successful_retry_notifies_the_admin_panel(self):
        waiter = await _create_user("mesero_rt_print", User.Role.MESERO)
        await database_sync_to_async(services.resize_tables)(1)
        order = await database_sync_to_async(services.create_order)(waiter, 1)
        await database_sync_to_async(services.add_item)(
            order, None, "Limonada", Decimal("4.50")
        )
        await database_sync_to_async(services.send_order)(order)
        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            await database_sync_to_async(kitchen_services.print_order)(order, waiter)

        communicator = await self._connected_admin_communicator()

        with _patched_adapter(FakePrinterAdapter()):
            await database_sync_to_async(kitchen_services.retry_print)(order, waiter)

        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response, {"type": "pedidos.actualizado"})
        await communicator.disconnect()

    async def test_failed_attempt_notifies_so_the_admin_sees_it_pending(self):
        waiter = await _create_user("mesero_rt_print2", User.Role.MESERO)
        await database_sync_to_async(services.resize_tables)(1)
        order = await database_sync_to_async(services.create_order)(waiter, 1)
        await database_sync_to_async(services.add_item)(
            order, None, "Limonada", Decimal("4.50")
        )
        await database_sync_to_async(services.send_order)(order)

        communicator = await self._connected_admin_communicator()

        with _patched_adapter(FakePrinterAdapter(fail_with=PrinterNotDetectedError)):
            await database_sync_to_async(kitchen_services.print_order)(order, waiter)

        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response, {"type": "pedidos.actualizado"})
        await communicator.disconnect()
