import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders import services
from apps.payments.models import Payment, PaymentAccount
from apps.payments.services import charge_order

User = get_user_model()


class ChargedOrdersViewTests(TestCase):
    """005 — GET /api/pedidos/cobrados, the admin's "Cobrados" tab."""

    def setUp(self):
        self.client = APIClient()
        services.resize_tables(3)
        self.waiter = User.objects.create_user(
            username="co_w", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="co_admin", password="clave1234", role=User.Role.ADMIN
        )
        self.account = PaymentAccount.objects.get(name="Efectivo")

    def _charged_order(self, table_number):
        order = services.create_order(self.waiter, table_number=table_number)
        services.add_item(order, name="Limonada", price=Decimal("4.50"))
        services.send_order(order)
        charge_order(order, self.admin, self.account)
        return order

    def test_lists_todays_charged_orders_newest_first_with_waiter(self):
        first = self._charged_order(1)
        second = self._charged_order(2)
        open_order = services.create_order(self.waiter, table_number=3)

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/pedidos/cobrados")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([o["id"] for o in response.data], [second.id, first.id])
        self.assertNotIn(open_order.id, [o["id"] for o in response.data])
        self.assertEqual(response.data[0]["waiter_username"], "co_w")
        self.assertIsNotNone(response.data[0]["active_payment"])

    def test_filters_by_the_given_date(self):
        order = self._charged_order(1)
        yesterday = timezone.now() - datetime.timedelta(days=1)
        Payment.objects.filter(order=order).update(charged_at=yesterday)

        self.client.force_authenticate(self.admin)
        today = self.client.get("/api/pedidos/cobrados")
        that_day = self.client.get(
            "/api/pedidos/cobrados",
            {"fecha": timezone.localtime(yesterday).date().isoformat()},
        )

        self.assertEqual(today.data, [])
        self.assertEqual([o["id"] for o in that_day.data], [order.id])

    def test_rejects_a_malformed_date(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/pedidos/cobrados", {"fecha": "11-10-2026"})
        self.assertEqual(response.status_code, 400)

    def test_waiter_gets_403(self):
        self.client.force_authenticate(self.waiter)
        self.assertEqual(self.client.get("/api/pedidos/cobrados").status_code, 403)
