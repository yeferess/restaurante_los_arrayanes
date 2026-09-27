from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders import services

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
