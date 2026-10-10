import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.menu.models import Category, Product
from apps.orders import services as order_services
from apps.payments.models import PaymentAccount
from apps.payments.services import charge_order

User = get_user_model()


class FullFlowIntegrationTests(APITestCase):
    """T21 — order sent, item added, charged → shows up correctly in
    /resumen, /rango and /movimiento (RF-1, RF-2, RF-3, RF-4, RF-6)."""

    def test_full_flow(self):
        order_services.resize_tables(1)
        waiter = User.objects.create_user(
            username="mesero_stats_flow", password="1234", role=User.Role.MESERO
        )
        admin = User.objects.create_user(
            username="admin_stats_flow", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        category = Category.objects.create(name="Bebidas")
        product = Product.objects.create(
            name="Limonada natural", category=category, price=Decimal("6000.00")
        )

        order = order_services.create_order(waiter, table_number=1)
        order_services.add_item(order, product_id=product.id, quantity=2)
        order_services.send_order(order)
        order.refresh_from_db()
        account = PaymentAccount.objects.get(name="Efectivo")
        charge_order(order, admin, account)
        order.refresh_from_db()

        today = datetime.date.today().isoformat()
        self.client.force_authenticate(admin)

        resumen = self.client.get(f"/api/estadisticas/resumen?date={today}")
        self.assertEqual(resumen.status_code, 200)
        self.assertEqual(resumen.data["money_total"], Decimal("12000.00"))
        self.assertEqual(resumen.data["orders_charged_count"], 1)
        self.assertEqual(
            resumen.data["top_products"],
            [{"product_name": "Limonada natural", "quantity": 2}],
        )

        rango = self.client.get(
            f"/api/estadisticas/rango?from={today}&to={today}"
        )
        self.assertEqual(rango.status_code, 200)
        self.assertEqual(rango.data["orders_sent_count"], 1)
        self.assertEqual(rango.data["money_total"], Decimal("12000.00"))

        movimiento = self.client.get(f"/api/estadisticas/movimiento?date={today}")
        self.assertEqual(movimiento.status_code, 200)
        self.assertEqual(
            movimiento.data["orders"][0]["daily_number"], order.daily_number
        )
        self.assertEqual(movimiento.data["orders"][0]["status"], "CHARGED")
        self.assertEqual(movimiento.data["payments"][0]["account_name"], "Efectivo")
