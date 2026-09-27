from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.menu.models import Category, Product
from apps.orders import services

User = get_user_model()


class AddItemViewTests(APITestCase):
    """T31 — POST /api/pedidos/{id}/items (RF-3, RF-4, RF-5)."""

    def setUp(self):
        services.resize_tables(1)
        self.waiter = User.objects.create_user(
            username="mesero_add_view", password="1234", role=User.Role.MESERO
        )
        self.other_waiter = User.objects.create_user(
            username="mesero_other_add", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.50")
        )
        self.order = services.create_order(self.waiter, table_number=1)

    def _url(self, order_id):
        return f"/api/pedidos/{order_id}/items"

    def _login(self, username="mesero_add_view"):
        self.client.post("/api/auth/mesero/login", {"username": username, "pin": "1234"})

    def test_adding_a_catalog_item(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"product_id": self.product.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Limonada")

    def test_adding_an_off_menu_item(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id),
            {"name": "Postre especial", "price": "6.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Postre especial")

    def test_invalid_off_menu_item_returns_400(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"name": "", "price": "6.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_product_returns_404(self):
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"product_id": 999999}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unavailable_product_returns_409(self):
        self.product.is_available = False
        self.product.save(update_fields=["is_available"])
        self._login()
        response = self.client.post(
            self._url(self.order.id), {"product_id": self.product.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_adding_to_a_charged_order_returns_409(self):
        self._login()
        admin = User.objects.create_user(
            username="admin_add_view", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        services.charge_order(self.order, admin)
        response = self.client.post(
            self._url(self.order.id), {"product_id": self.product.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_other_waiter_cannot_add_items(self):
        self._login("mesero_other_add")
        response = self.client.post(
            self._url(self.order.id), {"product_id": self.product.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(self.order.id), {"product_id": self.product.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
