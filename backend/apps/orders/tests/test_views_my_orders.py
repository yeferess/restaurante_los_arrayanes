from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services
from apps.orders.models import Order, Table

User = get_user_model()

MY_ORDERS_URL = "/api/pedidos/mios"


class MyOrdersViewTests(APITestCase):
    """T28 — GET /api/pedidos/mios (RF-8, RF-10, RF-13)."""

    def setUp(self):
        services.resize_tables(2)
        self.waiter = User.objects.create_user(
            username="mesero_mine", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_mine", password="1234", role=User.Role.MESERO
        )
        services.create_order(self.waiter, table_number=1)
        services.create_order(self.other_waiter, table_number=2)

    def _login(self, username, pin="1234"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": pin})

    def test_mesero_only_sees_own_orders(self):
        self._login("mesero_mine")
        response = self.client.get(MY_ORDERS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["table_number"], 1)

    def test_without_session_returns_401(self):
        response = self.client.get(MY_ORDERS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MyOrdersByDayViewTests(APITestCase):
    """RF-16 — GET /api/pedidos/mios?fecha=: today's orders plus the
    still-pending ones from earlier days; any other date, only that day."""

    def setUp(self):
        services.resize_tables(4)
        self.waiter = User.objects.create_user(
            username="mesero_day", password="1234", role=User.Role.MESERO
        )
        self.client.post("/api/auth/mesero/login", {"username": "mesero_day", "pin": "1234"})
        self.today = services.create_order(self.waiter, 1)
        self.yesterday_closed = self._yesterday_order(2, Order.Status.VOIDED, Table.Status.FREE)
        self.yesterday_open = self._yesterday_order(3, Order.Status.IN_PROGRESS, Table.Status.OCCUPIED)
        self.yesterday_paid = self._yesterday_order(4, Order.Status.CHARGED, Table.Status.PAID)

    def _yesterday_order(self, table_number, order_status, table_status):
        order = services.create_order(self.waiter, table_number)
        services.add_item(order, name="Sopa", price=8000)
        Order.objects.filter(pk=order.pk).update(
            status=order_status, created_at=timezone.now() - timedelta(days=1)
        )
        Table.objects.filter(number=table_number).update(status=table_status)
        return order

    def _ids(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return {order["id"] for order in response.data}

    def test_today_by_default_plus_pending_from_earlier_days(self):
        ids = self._ids(self.client.get(MY_ORDERS_URL))
        self.assertEqual(
            ids, {self.today.id, self.yesterday_open.id, self.yesterday_paid.id}
        )

    def test_paid_order_drops_out_once_its_table_is_released(self):
        Table.objects.filter(number=4).update(status=Table.Status.FREE)
        ids = self._ids(self.client.get(MY_ORDERS_URL))
        self.assertNotIn(self.yesterday_paid.id, ids)

    def test_previous_date_returns_only_that_day(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        ids = self._ids(self.client.get(MY_ORDERS_URL, {"fecha": yesterday}))
        self.assertEqual(
            ids,
            {self.yesterday_closed.id, self.yesterday_open.id, self.yesterday_paid.id},
        )

    def test_invalid_date_returns_400(self):
        response = self.client.get(MY_ORDERS_URL, {"fecha": "11-10-2026"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
