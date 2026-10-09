from django.apps import apps as django_apps
from rest_framework.test import APITestCase


class KitchenPrintingAppSetupTests(APITestCase):
    """T01 — the `kitchen_printing` app exists and is installed."""

    def test_kitchen_printing_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.kitchen_printing"))


class KitchenPrintingUrlsWiringTests(APITestCase):
    """T02 — `apps.kitchen_printing.urls` is wired under /api/ without
    breaking URL resolution for the rest of the project."""

    def test_unmapped_kitchen_printing_path_returns_404_not_500(self):
        response = self.client.get("/api/pedidos/no-existe-todavia/reimprimir")
        self.assertEqual(response.status_code, 404)

    def test_including_kitchen_printing_urls_does_not_break_existing_routes(self):
        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 401)
