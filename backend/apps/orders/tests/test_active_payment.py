from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.orders import services
from apps.payments.models import PaymentAccount

User = get_user_model()


class ActivePaymentInReadsTests(TestCase):
    """T19 — active_payment on pedidos/mios, pedidos/entrantes y
    pedidos/{id} (RF-3, RF-7)."""

    def setUp(self):
        self.client = APIClient()
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="ap_w", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="ap_admin", password="clave1234", role=User.Role.ADMIN
        )
        self.order = services.create_order(self.waiter, table_number=1)
        services.add_item(self.order, name="Limonada", price=Decimal("4.50"))
        services.send_order(self.order)

    def test_active_payment_is_null_before_charging(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.get("/api/pedidos/mios")
        self.assertIsNone(response.data[0]["active_payment"])

    def test_active_payment_appears_after_charging(self):
        account = PaymentAccount.objects.get(name="Efectivo")
        self.client.force_authenticate(self.admin)
        self.client.post(
            f"/api/pedidos/{self.order.id}/cobrar",
            {"account_id": account.id},
            format="json",
        )

        mine_response = APIClient()
        mine_response.force_authenticate(self.waiter)
        mine = mine_response.get("/api/pedidos/mios")
        self.assertEqual(mine.data[0]["active_payment"]["account_name"], "Efectivo")

        detail = mine_response.get(f"/api/pedidos/{self.order.id}")
        self.assertEqual(detail.data["active_payment"]["account_name"], "Efectivo")

    def test_active_payment_on_incoming_orders(self):
        services.resize_tables(2)
        order2 = services.create_order(self.waiter, table_number=2)
        services.add_item(order2, name="Jugo", price=Decimal("5.00"))
        services.send_order(order2)

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/pedidos/entrantes")
        by_id = {order["id"]: order for order in response.data}
        self.assertIsNone(by_id[order2.id]["active_payment"])
