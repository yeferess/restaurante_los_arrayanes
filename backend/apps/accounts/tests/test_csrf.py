from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

TRUSTED_ORIGIN = "http://localhost:3000"
UNTRUSTED_ORIGIN = "http://evil.example.com"


class CsrfProtectionTests(APITestCase):
    """CSRF protection between the SPA frontend and the session-cookie API.

    Uses APIClient(enforce_csrf_checks=True) because the default test
    client disables CSRF enforcement — real browser requests do not.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_csrf", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def test_admin_login_sets_a_csrftoken_cookie(self):
        response = self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_csrf", "password": "Sup3rSecreta"},
        )
        self.assertIn("csrftoken", response.cookies)

    def test_mesero_login_sets_a_csrftoken_cookie(self):
        User.objects.create_user(
            username="mesero_csrf", password="1234", role=User.Role.MESERO
        )
        response = self.client.post(
            "/api/auth/mesero/login", {"username": "mesero_csrf", "pin": "1234"}
        )
        self.assertIn("csrftoken", response.cookies)

    def _login_with_csrf_enforced(self):
        client = APIClient(enforce_csrf_checks=True)
        login = client.post(
            "/api/auth/admin/login",
            {"username": "admin_csrf", "password": "Sup3rSecreta"},
        )
        csrf_token = login.cookies["csrftoken"].value
        return client, csrf_token

    def test_authenticated_post_without_a_csrf_token_is_rejected(self):
        client, _csrf_token = self._login_with_csrf_enforced()
        response = client.post("/api/auth/heartbeat", HTTP_ORIGIN=TRUSTED_ORIGIN)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_post_from_an_untrusted_origin_is_rejected(self):
        client, csrf_token = self._login_with_csrf_enforced()
        response = client.post(
            "/api/auth/heartbeat",
            HTTP_ORIGIN=UNTRUSTED_ORIGIN,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_post_with_csrf_token_and_trusted_origin_succeeds(self):
        client, csrf_token = self._login_with_csrf_enforced()
        response = client.post(
            "/api/auth/heartbeat",
            HTTP_ORIGIN=TRUSTED_ORIGIN,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
