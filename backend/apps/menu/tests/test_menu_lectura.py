from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.menu.models import Category, Product

User = get_user_model()

MENU_URL = "/api/menu"


class MenuReadViewTests(APITestCase):
    """T22 — GET /api/menu (RF-7)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_menu_read", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_menu_read", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")
        self.available = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.00")
        )
        self.unavailable = Product.objects.create(
            name="Jugo de mango",
            category=self.category,
            price=Decimal("5.00"),
            is_available=False,
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_menu_read", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_menu_read", "pin": "1234"}
        )

    def test_without_session_returns_401(self):
        response = self.client.get(MENU_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mesero_sees_only_available_products_with_category(self):
        self._login_mesero()
        response = self.client.get(MENU_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data]
        self.assertEqual(names, ["Limonada"])
        self.assertEqual(response.data[0]["category"]["name"], "Bebidas")

    def test_admin_can_also_read_the_mesero_menu(self):
        self._login_admin()
        response = self.client.get(MENU_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data]
        self.assertEqual(names, ["Limonada"])
