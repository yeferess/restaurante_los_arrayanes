from django.conf import settings
from django.test import SimpleTestCase


class SessionSettingsTests(SimpleTestCase):
    """T02 — Django sessions must be hardened and backed by the project's SQLite database."""

    def test_session_cookie_is_httponly(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    def test_session_cookie_samesite_is_strict(self):
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Strict")

    def test_session_engine_is_database_backed(self):
        self.assertEqual(
            settings.SESSION_ENGINE, "django.contrib.sessions.backends.db"
        )

    def test_default_database_is_sqlite(self):
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3"
        )

    def test_sessions_app_is_installed(self):
        self.assertIn("django.contrib.sessions", settings.INSTALLED_APPS)
