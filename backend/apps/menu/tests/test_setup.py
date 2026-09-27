from django.apps import apps as django_apps
from rest_framework.test import APITestCase


class MenuAppSetupTests(APITestCase):
    """T01 — the `menu` app exists and is installed."""

    def test_menu_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.menu"))


class MenuUrlsWiringTests(APITestCase):
    """T02 — `apps.menu.urls` is wired under /api/ without breaking
    URL resolution for the rest of the project."""

    def test_unmapped_menu_path_returns_404_not_500(self):
        response = self.client.get("/api/menu/no-existe-todavia")
        self.assertEqual(response.status_code, 404)

    def test_including_menu_urls_does_not_break_existing_routes(self):
        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 401)
