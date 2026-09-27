from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.services import attempt_login

User = get_user_model()


class BasicLoginServiceTests(TestCase):
    """T11 — attempt_login() happy/unhappy path, no lockout yet (RF-1)."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_login", password="1234", role=User.Role.MESERO
        )

    def test_correct_credentials_succeed(self):
        result = attempt_login(
            username="mesero_login", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertTrue(result.success)
        self.assertEqual(result.user, self.mesero)

    def test_wrong_password_fails_and_does_not_crash(self):
        # Exact wording for an existing account's wrong password is pinned
        # down by T15 (test_services_messages.py); here we only check the
        # attempt is rejected.
        result = attempt_login(
            username="mesero_login", credential="9999", expected_role=User.Role.MESERO
        )
        self.assertFalse(result.success)

    def test_nonexistent_username_fails_without_revealing_existence(self):
        # Exact message shape (simulated attempts counter) is pinned down
        # by T16 (test_services_nonexistent_username.py).
        result = attempt_login(
            username="no_existe", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertFalse(result.success)
        self.assertTrue(result.message.startswith("Usuario o contraseña incorrectos."))

    def test_wrong_role_is_treated_like_nonexistent(self):
        # A mesero account trying to authenticate against the admin role
        # must not be distinguishable from a non-existent admin (RF-1).
        result = attempt_login(
            username="mesero_login", credential="1234", expected_role=User.Role.ADMIN
        )
        self.assertFalse(result.success)
        self.assertTrue(result.message.startswith("Usuario o contraseña incorrectos."))
