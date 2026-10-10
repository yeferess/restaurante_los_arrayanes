from django.apps import apps as django_apps
from rest_framework.test import APITestCase


class StatsAppSetupTests(APITestCase):
    """T01 — the `stats` app exists and is installed."""

    def test_stats_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.stats"))


class StatsUrlsWiringTests(APITestCase):
    """T02 — `apps.stats.urls` is wired under /api/ without breaking URL
    resolution for the rest of the project."""

    def test_unmapped_stats_path_returns_404_not_500(self):
        response = self.client.get("/api/estadisticas/no-existe-todavia")
        self.assertEqual(response.status_code, 404)

    def test_resumen_without_session_returns_401(self):
        response = self.client.get("/api/estadisticas/resumen")
        self.assertEqual(response.status_code, 401)

    def test_including_stats_urls_does_not_break_existing_routes(self):
        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 401)
