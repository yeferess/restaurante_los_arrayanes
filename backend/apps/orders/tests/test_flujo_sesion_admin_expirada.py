"""T94 — escenario: el computador del admin queda sin uso, su sesión
expira por inactividad (001 RF-8) y dos meseros siguen trabajando.

Reproduce lo que vio el admin ("un pedido llegó al instante y el otro
apareció mucho después") y separa las tres causas posibles:

1. La sesión expira pero el WebSocket ya abierto sigue recibiendo avisos;
   la lista del panel responde 401 hasta volver a entrar.
2. (Frontend) el socket reconecta sin volver a pedir la lista — ver
   `frontend/lib/api/ordersSocket.test.ts`.
3. Un pedido en borrador no avisa ni imprime hasta que se envía.

En todos los casos la cocina imprime sin depender de la sesión del admin.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from asgiref.sync import sync_to_async
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.middleware import LAST_ACTIVITY_SESSION_KEY
from apps.kitchen_printing.adapters import PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter
from apps.kitchen_printing.models import PrintJob
from apps.orders import services
from apps.orders.models import Order
from apps.orders.routing import websocket_urlpatterns

User = get_user_model()

application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))

ADMIN_PASSWORD = "Sup3rSecreta"
INCOMING_URL = "/api/pedidos/entrantes"
NOTIFICATION = {"type": "pedidos.actualizado"}


class AdminSessionExpiredScenarioTests(TestCase):
    def setUp(self):
        services.resize_tables(4)
        User.objects.create_user(
            username="admin_turno", password=ADMIN_PASSWORD, role=User.Role.ADMIN
        )
        self.mesero1 = User.objects.create_user(
            username="mesero_uno", password="1234", role=User.Role.MESERO
        )
        self.mesero2 = User.objects.create_user(
            username="mesero_dos", password="1234", role=User.Role.MESERO
        )
        self.printer = FakePrinterAdapter()
        patcher = patch(
            "apps.kitchen_printing.services.get_printer_adapter",
            side_effect=lambda: self.printer,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.admin_client = APIClient()
        response = self.admin_client.post(
            "/api/auth/admin/login",
            {"username": "admin_turno", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 200, response.content

    # --- helpers -----------------------------------------------------------

    def _session_key(self):
        return self.admin_client.cookies["sessionid"].value

    def _expire_admin_session(self):
        """El computador queda 31 min sin uso: nadie mueve el mouse, así
        que el heartbeat no renueva `ultima_actividad`."""
        session = SessionStore(session_key=self._session_key())
        session[LAST_ACTIVITY_SESSION_KEY] = (
            timezone.now() - timedelta(minutes=31)
        ).isoformat()
        session.save()

    def _login_again(self):
        response = self.admin_client.post(
            "/api/auth/admin/login",
            {"username": "admin_turno", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 200, response.content

    def _incoming(self):
        return self.admin_client.get(INCOMING_URL)

    def _sent_order(self, waiter, table, name, price):
        order = services.create_order(waiter, table_number=table)
        services.add_item(order, name=name, price=Decimal(price))
        services.send_order(order)
        return order

    async def _admin_socket(self, session_key=None):
        key = session_key or await sync_to_async(self._session_key)()
        communicator = WebsocketCommunicator(
            application,
            "/ws/pedidos/",
            headers=[(b"cookie", f"sessionid={key}".encode())],
        )
        connected, _ = await communicator.connect()
        return communicator, connected

    # --- escenario completo -------------------------------------------------

    async def test_full_scenario_nothing_is_lost_only_hidden_until_login(self):
        communicator, connected = await self._admin_socket()
        self.assertTrue(connected)

        # 1. Antes de expirar: mesero1 envía y el admin lo ve al instante.
        order1 = await database_sync_to_async(self._sent_order)(
            self.mesero1, 1, "Bandeja paisa", "25000"
        )
        self.assertEqual(await communicator.receive_json_from(timeout=1), NOTIFICATION)
        response = await sync_to_async(self._incoming)()
        self.assertEqual(response.status_code, 200)
        self.assertEqual([o["id"] for o in response.data], [order1.id])
        self.assertEqual(self.printer.call_count, 1)

        # mesero2 ya tenía su pedido enviado antes de que el PC quedara solo.
        order2 = await database_sync_to_async(self._sent_order)(
            self.mesero2, 2, "Limonada", "5000"
        )
        await communicator.receive_json_from(timeout=1)

        # 2. El PC queda sin uso y la sesión expira.
        await sync_to_async(self._expire_admin_session)()

        # Los dos meseros agregan ítems a sus pedidos.
        await database_sync_to_async(services.add_item)(
            order1, name="Jugo de mora", price=Decimal("6000")
        )
        await database_sync_to_async(services.add_item)(
            order2, name="Churrasco", price=Decimal("32000")
        )

        # El socket ya abierto sigue recibiendo los dos avisos...
        self.assertEqual(await communicator.receive_json_from(timeout=1), NOTIFICATION)
        self.assertEqual(await communicator.receive_json_from(timeout=1), NOTIFICATION)
        # ...pero la lista que pide el panel responde 401: no se ve nada nuevo.
        response = await sync_to_async(self._incoming)()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Sesión expirada por inactividad.")

        # La cocina imprimió las dos adiciones sin depender del admin.
        self.assertEqual(self.printer.call_count, 4)
        self.assertEqual(
            await database_sync_to_async(
                PrintJob.objects.filter(ticket_type=PrintJob.TicketType.ADDITION).count
            )(),
            2,
        )

        # 4. Un socket nuevo con la sesión cerrada se rechaza.
        old_key = await sync_to_async(self._session_key)()
        rejected, rejected_ok = await self._admin_socket(old_key)
        self.assertFalse(rejected_ok)
        await communicator.disconnect()

        # 3. Al volver a entrar aparecen los dos pedidos con todos sus ítems.
        await sync_to_async(self._login_again)()
        response = await sync_to_async(self._incoming)()
        self.assertEqual(response.status_code, 200)
        by_id = {o["id"]: o for o in response.data}
        self.assertEqual(set(by_id), {order1.id, order2.id})
        self.assertEqual(
            [i["name"] for i in by_id[order1.id]["items"]],
            ["Bandeja paisa", "Jugo de mora"],
        )
        self.assertEqual(
            [i["name"] for i in by_id[order2.id]["items"]],
            ["Limonada", "Churrasco"],
        )
        self.assertFalse(by_id[order1.id]["has_pending_print"])
        self.assertFalse(by_id[order2.id]["has_pending_print"])

    # --- piezas del escenario por separado ----------------------------------

    def test_any_admin_request_after_31_minutes_returns_401(self):
        self._expire_admin_session()
        response = self._incoming()
        self.assertEqual(response.status_code, 401)
        # La sesión quedó cerrada: la siguiente petición tampoco entra.
        self.assertNotEqual(self._incoming().status_code, 200)
        # Y /api/auth/session lo confirma: es lo que usa el panel para
        # mandar al admin a volver a entrar (T94).
        self.assertNotEqual(self.admin_client.get("/api/auth/session").status_code, 200)

    def test_the_panels_own_refreshes_do_not_keep_the_session_alive(self):
        """Solo el login y el heartbeat renuevan la actividad; pedir la
        lista (lo que hace el panel al recibir un aviso) no la renueva."""
        session = SessionStore(session_key=self._session_key())
        before = session[LAST_ACTIVITY_SESSION_KEY]
        self.assertEqual(self._incoming().status_code, 200)
        session = SessionStore(session_key=self._session_key())
        self.assertEqual(session[LAST_ACTIVITY_SESSION_KEY], before)

    async def test_items_in_a_draft_do_not_notify_or_print_until_sent(self):
        communicator, connected = await self._admin_socket()
        self.assertTrue(connected)

        draft = await database_sync_to_async(services.create_order)(
            self.mesero2, table_number=3
        )
        await database_sync_to_async(services.add_item)(
            draft, name="Sancocho", price=Decimal("18000")
        )
        await database_sync_to_async(services.add_item)(
            draft, name="Gaseosa", price=Decimal("4000")
        )

        self.assertTrue(await communicator.receive_nothing(timeout=0.3))
        response = await sync_to_async(self._incoming)()
        self.assertEqual(response.data, [])
        self.assertEqual(self.printer.call_count, 0)

        await database_sync_to_async(services.send_order)(draft)
        self.assertEqual(await communicator.receive_json_from(timeout=1), NOTIFICATION)
        response = await sync_to_async(self._incoming)()
        self.assertEqual([o["id"] for o in response.data], [draft.id])
        self.assertEqual(self.printer.call_count, 1)
        await communicator.disconnect()

    def test_two_waiters_at_once_each_get_their_own_number_and_ticket(self):
        order1 = self._sent_order(self.mesero1, 1, "Bandeja paisa", "25000")
        order2 = self._sent_order(self.mesero2, 2, "Limonada", "5000")
        services.add_item(order1, name="Arepa", price=Decimal("3000"))
        services.add_item(order2, name="Arepa", price=Decimal("3000"))

        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertNotEqual(order1.daily_number, order2.daily_number)

        response = self._incoming()
        by_id = {o["id"]: o for o in response.data}
        self.assertEqual(by_id[order1.id]["waiter_username"], "mesero_uno")
        self.assertEqual(by_id[order2.id]["waiter_username"], "mesero_dos")
        self.assertEqual(len(by_id[order1.id]["items"]), 2)
        self.assertEqual(len(by_id[order2.id]["items"]), 2)
        self.assertEqual(PrintJob.objects.filter(order=order1).count(), 2)
        self.assertEqual(PrintJob.objects.filter(order=order2).count(), 2)
        self.assertEqual(self.printer.call_count, 4)

    def test_a_failed_kitchen_print_still_shows_the_order_marked_pending(self):
        order1 = self._sent_order(self.mesero1, 1, "Bandeja paisa", "25000")
        self.printer.fail_with = PrinterNotDetectedError
        order2 = self._sent_order(self.mesero2, 2, "Limonada", "5000")

        response = self._incoming()
        by_id = {o["id"]: o for o in response.data}
        self.assertEqual(set(by_id), {order1.id, order2.id})
        self.assertFalse(by_id[order1.id]["has_pending_print"])
        self.assertTrue(by_id[order2.id]["has_pending_print"])
        self.assertEqual(Order.objects.get(pk=order2.pk).status, Order.Status.IN_PROGRESS)
