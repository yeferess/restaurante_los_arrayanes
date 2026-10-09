from decimal import Decimal

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase

from apps.orders import services
from apps.orders.routing import websocket_urlpatterns
from apps.payments import services as payment_services
from apps.payments.models import PaymentAccount

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


@database_sync_to_async
def _efectivo():
    return PaymentAccount.objects.get(name="Efectivo")


class VoidChargeRealtimeTests(TestCase):
    """T20 — a successful void_charge notifies connected admins in real
    time; charging and a rejected void do not (RF-6)."""

    async def _connected_admin_communicator(self):
        admin = await _create_user(
            "admin_rt_pay", User.Role.ADMIN, password="Sup3rSecreta"
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

    async def test_voiding_a_charge_notifies(self):
        waiter = await _create_user("mesero_rt_pay", User.Role.MESERO)
        charging_admin = await _create_user(
            "charge_admin_rt_pay", User.Role.ADMIN, password="Sup3rSecreta"
        )
        await database_sync_to_async(services.resize_tables)(1)
        order = await database_sync_to_async(services.create_order)(waiter, 1)
        await database_sync_to_async(services.add_item)(
            order, None, "Limonada", Decimal("4.50")
        )
        await database_sync_to_async(services.send_order)(order)
        account = await _efectivo()
        await database_sync_to_async(payment_services.charge_order)(
            order, charging_admin, account
        )

        communicator = await self._connected_admin_communicator()

        await database_sync_to_async(payment_services.void_charge)(
            order, charging_admin, "Cuenta equivocada"
        )

        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response, {"type": "pedidos.actualizado"})
        await communicator.disconnect()

    async def test_charging_does_not_notify(self):
        waiter = await _create_user("mesero_rt_pay2", User.Role.MESERO)
        admin = await _create_user(
            "admin_rt_pay2", User.Role.ADMIN, password="Sup3rSecreta"
        )
        await database_sync_to_async(services.resize_tables)(1)
        order = await database_sync_to_async(services.create_order)(waiter, 1)
        await database_sync_to_async(services.add_item)(
            order, None, "Limonada", Decimal("4.50")
        )
        await database_sync_to_async(services.send_order)(order)
        account = await _efectivo()

        communicator = await self._connected_admin_communicator()

        await database_sync_to_async(payment_services.charge_order)(
            order, admin, account
        )

        self.assertTrue(await communicator.receive_nothing(timeout=0.3))
        await communicator.disconnect()

    async def test_a_rejected_void_does_not_notify(self):
        waiter = await _create_user("mesero_rt_pay3", User.Role.MESERO)
        admin = await _create_user(
            "admin_rt_pay3", User.Role.ADMIN, password="Sup3rSecreta"
        )
        await database_sync_to_async(services.resize_tables)(1)
        order = await database_sync_to_async(services.create_order)(waiter, 1)
        await database_sync_to_async(services.add_item)(
            order, None, "Limonada", Decimal("4.50")
        )
        await database_sync_to_async(services.send_order)(order)

        communicator = await self._connected_admin_communicator()

        async def _attempt():
            try:
                await database_sync_to_async(payment_services.void_charge)(
                    order, admin, "motivo"
                )
            except Exception:
                pass

        await _attempt()

        self.assertTrue(await communicator.receive_nothing(timeout=0.3))
        await communicator.disconnect()
