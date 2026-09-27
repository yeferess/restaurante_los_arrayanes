from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.menu.models import Category, Product

User = get_user_model()

PRODUCTS_URL = "/api/menu/productos"


class ProductListCreateViewTests(APITestCase):
    """T18 — GET/POST /api/menu/productos (RF-2)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_prod", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_prod", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_prod", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_prod", "pin": "1234"}
        )

    def test_get_without_session_returns_401(self):
        response = self.client.get(PRODUCTS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.get(PRODUCTS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_as_admin_includes_unavailable_products(self):
        Product.objects.create(
            name="Limonada",
            category=self.category,
            price=Decimal("4.00"),
            is_available=False,
        )
        self._login_admin()
        response = self.client.get(PRODUCTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertFalse(response.data[0]["is_available"])

    def test_post_as_admin_creates_product(self):
        self._login_admin()
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": self.category.pk, "price": 4.5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Limonada")
        self.assertEqual(response.data["category"]["id"], self.category.pk)
        self.assertTrue(response.data["is_available"])
        self.assertTrue(Product.objects.filter(name="Limonada").exists())

    def test_post_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": self.category.pk, "price": 4.5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_without_session_returns_401(self):
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": self.category.pk, "price": 4.5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_with_invalid_price_returns_400(self):
        self._login_admin()
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": self.category.pk, "price": 0},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_with_non_numeric_price_returns_400(self):
        self._login_admin()
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": self.category.pk, "price": "gratis"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_with_nonexistent_category_returns_400(self):
        self._login_admin()
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": 999999, "price": 4.5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_with_duplicate_name_returns_409(self):
        Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.00")
        )
        self._login_admin()
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "LIMONADA", "category_id": self.category.pk, "price": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_post_without_specifying_availability_defaults_to_true(self):
        self._login_admin()
        response = self.client.post(
            PRODUCTS_URL,
            {"name": "Limonada", "category_id": self.category.pk, "price": 4.5},
            format="json",
        )
        self.assertTrue(response.data["is_available"])


class ProductDetailPatchViewTests(APITestCase):
    """T19 — PATCH /api/menu/productos/{id} (RF-3)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_prod2", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_prod2", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")
        self.other_category = Category.objects.create(name="Postres")
        self.product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.00")
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_prod2", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_prod2", "pin": "1234"}
        )

    def _url(self, product_id):
        return f"{PRODUCTS_URL}/{product_id}"

    def test_patch_edits_name_category_and_price(self):
        self._login_admin()
        response = self.client.patch(
            self._url(self.product.pk),
            {
                "name": "Limonada natural",
                "category_id": self.other_category.pk,
                "price": 5.5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Limonada natural")
        self.assertEqual(self.product.category_id, self.other_category.pk)
        self.assertEqual(self.product.price, Decimal("5.5"))

    def test_patch_nonexistent_product_returns_404(self):
        self._login_admin()
        response = self.client.patch(
            self._url(999999), {"name": "Nueva"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_with_nonexistent_category_returns_400(self):
        self._login_admin()
        response = self.client.patch(
            self._url(self.product.pk), {"category_id": 999999}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_with_duplicate_name_returns_409(self):
        Product.objects.create(
            name="Te helado", category=self.category, price=Decimal("3.00")
        )
        self._login_admin()
        response = self.client.patch(
            self._url(self.product.pk), {"name": "te helado"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_patch_with_invalid_price_returns_400(self):
        self._login_admin()
        response = self.client.patch(
            self._url(self.product.pk), {"price": 0}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.patch(
            self._url(self.product.pk), {"name": "Nueva"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_without_session_returns_401(self):
        response = self.client.patch(
            self._url(self.product.pk), {"name": "Nueva"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductAvailabilityViewTests(APITestCase):
    """T20 — POST /api/menu/productos/{id}/disponibilidad (RF-4)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_prod3", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_prod3", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.00")
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_prod3", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_prod3", "pin": "1234"}
        )

    def _url(self, product_id):
        return f"{PRODUCTS_URL}/{product_id}/disponibilidad"

    def test_marking_unavailable(self):
        self._login_admin()
        response = self.client.post(
            self._url(self.product.pk), {"is_available": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_available)

    def test_marking_available_again(self):
        self.product.is_available = False
        self.product.save(update_fields=["is_available"])
        self._login_admin()
        response = self.client.post(
            self._url(self.product.pk), {"is_available": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_available)

    def test_missing_field_returns_400(self):
        self._login_admin()
        response = self.client.post(self._url(self.product.pk), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_product_returns_404(self):
        self._login_admin()
        response = self.client.post(
            self._url(999999), {"is_available": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.post(
            self._url(self.product.pk), {"is_available": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(self.product.pk), {"is_available": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductDeleteViewTests(APITestCase):
    """T21 — DELETE /api/menu/productos/{id} (RF-5)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_prod4", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_prod4", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.00")
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_prod4", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_prod4", "pin": "1234"}
        )

    def _url(self, product_id):
        return f"{PRODUCTS_URL}/{product_id}"

    def test_delete_as_admin_removes_the_product(self):
        self._login_admin()
        response = self.client.delete(self._url(self.product.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_delete_an_unavailable_product_also_succeeds(self):
        self.product.is_available = False
        self.product.save(update_fields=["is_available"])
        self._login_admin()
        response = self.client.delete(self._url(self.product.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_nonexistent_product_returns_404(self):
        self._login_admin()
        response = self.client.delete(self._url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.delete(self._url(self.product.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_without_session_returns_401(self):
        response = self.client.delete(self._url(self.product.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
