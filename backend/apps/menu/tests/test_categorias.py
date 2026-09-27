from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from decimal import Decimal

from apps.menu.models import Category, Product

User = get_user_model()

CATEGORIES_URL = "/api/menu/categorias"


class CategoryListCreateViewTests(APITestCase):
    """T15 — GET/POST /api/menu/categorias (RF-1)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_menu", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_menu", password="1234", role=User.Role.MESERO
        )

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_menu", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_menu", "pin": "1234"}
        )

    def test_get_without_session_returns_401(self):
        response = self.client.get(CATEGORIES_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.get(CATEGORIES_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_as_admin_returns_categories(self):
        Category.objects.create(name="Bebidas")
        self._login_admin()
        response = self.client.get(CATEGORIES_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Bebidas", [c["name"] for c in response.data])

    def test_post_as_admin_creates_category(self):
        self._login_admin()
        response = self.client.post(CATEGORIES_URL, {"name": "Bebidas"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Bebidas")
        self.assertTrue(Category.objects.filter(name="Bebidas").exists())

    def test_post_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.post(CATEGORIES_URL, {"name": "Bebidas"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_without_session_returns_401(self):
        response = self.client.post(CATEGORIES_URL, {"name": "Bebidas"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_with_empty_name_returns_400(self):
        self._login_admin()
        response = self.client.post(CATEGORIES_URL, {"name": "   "})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_with_duplicate_name_returns_409(self):
        Category.objects.create(name="Bebidas")
        self._login_admin()
        response = self.client.post(CATEGORIES_URL, {"name": "BEBIDAS"})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class CategoryDetailViewTests(APITestCase):
    """T16 — PATCH /api/menu/categorias/{id} (RF-1)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_menu2", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_menu2", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_menu2", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_menu2", "pin": "1234"}
        )

    def _url(self, category_id):
        return f"{CATEGORIES_URL}/{category_id}"

    def test_patch_as_admin_renames_the_category(self):
        self._login_admin()
        response = self.client.patch(
            self._url(self.category.pk), {"name": "Refrescos"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Refrescos")
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Refrescos")

    def test_patch_nonexistent_category_returns_404(self):
        self._login_admin()
        response = self.client.patch(
            self._url(999999), {"name": "Refrescos"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_with_duplicate_name_returns_409(self):
        Category.objects.create(name="Postres")
        self._login_admin()
        response = self.client.patch(
            self._url(self.category.pk), {"name": "postres"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_patch_with_empty_name_returns_400(self):
        self._login_admin()
        response = self.client.patch(
            self._url(self.category.pk), {"name": "   "}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.patch(
            self._url(self.category.pk), {"name": "Refrescos"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_without_session_returns_401(self):
        response = self.client.patch(
            self._url(self.category.pk), {"name": "Refrescos"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CategoryDeleteViewTests(APITestCase):
    """T17 — DELETE /api/menu/categorias/{id} (RF-1)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_menu3", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_menu3", password="1234", role=User.Role.MESERO
        )
        self.category = Category.objects.create(name="Bebidas")

    def _login_admin(self):
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_menu3", "password": "Sup3rSecreta"},
        )

    def _login_mesero(self):
        self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_menu3", "pin": "1234"}
        )

    def _url(self, category_id):
        return f"{CATEGORIES_URL}/{category_id}"

    def test_delete_without_products_succeeds(self):
        self._login_admin()
        response = self.client.delete(self._url(self.category.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())

    def test_delete_with_products_assigned_returns_409(self):
        Product.objects.create(
            name="Limonada", category=self.category, price=Decimal("4.00")
        )
        self._login_admin()
        response = self.client.delete(self._url(self.category.pk))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_delete_nonexistent_category_returns_404(self):
        self._login_admin()
        response = self.client.delete(self._url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_as_mesero_returns_403(self):
        self._login_mesero()
        response = self.client.delete(self._url(self.category.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_without_session_returns_401(self):
        response = self.client.delete(self._url(self.category.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
