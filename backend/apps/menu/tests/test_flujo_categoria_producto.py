from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.menu.models import Category, Product

User = get_user_model()

CATEGORIES_URL = "/api/menu/categorias"
PRODUCTS_URL = "/api/menu/productos"


class CategoryProductLifecycleFlowTests(APITestCase):
    """T32 — end-to-end: crear categoría → crear producto → intentar
    eliminar la categoría (409) → eliminar el producto → eliminar la
    categoría (204) (RF-1, RF-2, RF-5)."""

    def setUp(self):
        User.objects.create_user(
            username="admin_flujo", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_flujo", "password": "Sup3rSecreta"},
        )

    def test_full_lifecycle(self):
        create_response = self.client.post(CATEGORIES_URL, {"name": "Bebidas"})
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        category_id = create_response.data["id"]

        product_response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": category_id, "price": 4.5},
            format="json",
        )
        self.assertEqual(product_response.status_code, status.HTTP_201_CREATED)
        product_id = product_response.data["id"]

        blocked_delete = self.client.delete(f"{CATEGORIES_URL}/{category_id}")
        self.assertEqual(blocked_delete.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Category.objects.filter(pk=category_id).exists())

        delete_product = self.client.delete(f"{PRODUCTS_URL}/{product_id}")
        self.assertEqual(delete_product.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=product_id).exists())

        delete_category = self.client.delete(f"{CATEGORIES_URL}/{category_id}")
        self.assertEqual(delete_category.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category_id).exists())
