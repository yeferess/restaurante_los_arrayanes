from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.orders import services as order_services
from apps.payments.models import PaymentAccount
from apps.payments.services import charge_order

User = get_user_model()


class StatsViewsTestCase(APITestCase):
    def setUp(self):
        order_services.resize_tables(1)
        self.admin = User.objects.create_user(
            username="admin_stats_v", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username="mesero_stats_v", password="1234", role=User.Role.MESERO
        )

    def _charge_today(self):
        order = order_services.create_order(self.waiter, table_number=1)
        order_services.add_item(order, name="Limonada", price=Decimal("5000.00"))
        order_services.send_order(order)
        account = PaymentAccount.objects.get(name="Efectivo")
        charge_order(order, self.admin, account)
        return order


class DaySummaryViewTests(StatsViewsTestCase):
    """T11 — GET /api/estadisticas/resumen (RF-1 a RF-4, RF-8)."""

    def _url(self, date=None):
        return "/api/estadisticas/resumen" + (f"?date={date}" if date else "")

    def test_admin_gets_todays_summary_by_default(self):
        self._charge_today()
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["money_total"], Decimal("5000.00"))
        self.assertEqual(response.data["orders_charged_count"], 1)

    def test_invalid_date_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url("no-es-una-fecha"))
        self.assertEqual(response.status_code, 400)

    def test_mesero_gets_403(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)

    def test_without_session_returns_401(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 401)


class RangeSummaryViewTests(StatsViewsTestCase):
    """T12 — GET /api/estadisticas/rango (RF-5, RF-8)."""

    def _url(self, from_=None, to=None):
        return f"/api/estadisticas/rango?from={from_}&to={to}"

    def test_admin_gets_the_range_summary(self):
        self._charge_today()
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url("2020-01-01", "2030-01-01"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["orders_sent_count"], 1)

    def test_missing_params_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/estadisticas/rango")
        self.assertEqual(response.status_code, 400)

    def test_from_after_to_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url("2026-01-10", "2026-01-01"))
        self.assertEqual(response.status_code, 400)

    def test_mesero_gets_403(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.get(self._url("2020-01-01", "2030-01-01"))
        self.assertEqual(response.status_code, 403)

    def test_without_session_returns_401(self):
        response = self.client.get(self._url("2020-01-01", "2030-01-01"))
        self.assertEqual(response.status_code, 401)


class DayMovementViewTests(StatsViewsTestCase):
    """T13 — GET /api/estadisticas/movimiento (RF-6, RF-7, RF-8)."""

    def _url(self, date=None):
        return "/api/estadisticas/movimiento" + (f"?date={date}" if date else "")

    def test_admin_gets_todays_movement_by_default(self):
        self._charge_today()
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["orders"]), 1)
        self.assertEqual(len(response.data["payments"]), 1)

    def test_identifies_orders_by_daily_number_not_internal_id(self):
        order = self._charge_today()
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url())
        self.assertEqual(
            response.data["orders"][0]["daily_number"], order.daily_number
        )
        self.assertNotIn("id", response.data["orders"][0])

    def test_invalid_date_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self._url("no-es-una-fecha"))
        self.assertEqual(response.status_code, 400)

    def test_mesero_gets_403(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)

    def test_without_session_returns_401(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 401)
