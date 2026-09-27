from django.apps import apps as django_apps
from rest_framework.test import APITestCase


class OrdersAppSetupTests(APITestCase):
    """T01 — the `orders` app exists and is installed."""

    def test_orders_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.orders"))


class OrdersUrlsWiringTests(APITestCase):
    """T02 — `apps.orders.urls` is wired under /api/ without breaking
    URL resolution for the rest of the project."""

    def test_unmapped_orders_path_returns_404_not_500(self):
        response = self.client.get("/api/pedidos/no-existe-todavia")
        self.assertEqual(response.status_code, 404)

    def test_including_orders_urls_does_not_break_existing_routes(self):
        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 401)
