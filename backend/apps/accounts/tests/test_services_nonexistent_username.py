import re

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import FailedLoginAttempt
from apps.accounts.services import attempt_login

User = get_user_model()

MESSAGE_PATTERN = re.compile(
    r"^Usuario o contraseña incorrectos\. Te quedan (\d) intentos antes del bloqueo\.$"
)


class NonexistentUsernameSimulatedCounterTests(TestCase):
    """T16 — a non-existent username gets the same message shape as a real
    account, without ever writing a FailedLoginAttempt row (RF-1)."""

    def test_message_has_the_same_shape_as_a_real_account(self):
        result = attempt_login(
            username="fantasma", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertFalse(result.success)
        match = MESSAGE_PATTERN.match(result.message)
        self.assertIsNotNone(match)
        remaining = int(match.group(1))
        self.assertGreaterEqual(remaining, 1)
        self.assertLessEqual(remaining, 5)

    def test_no_failed_login_attempt_row_is_persisted(self):
        attempt_login(
            username="fantasma2", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertEqual(FailedLoginAttempt.objects.count(), 0)

    def test_same_username_yields_a_stable_count_across_calls(self):
        first = attempt_login(
            username="fantasma3", credential="a", expected_role=User.Role.MESERO
        )
        second = attempt_login(
            username="fantasma3", credential="b", expected_role=User.Role.MESERO
        )
        self.assertEqual(first.message, second.message)

    def test_wrong_role_reuses_the_same_simulated_counter(self):
        mesero_attempt = attempt_login(
            username="fantasma4", credential="1234", expected_role=User.Role.MESERO
        )
        admin_attempt = attempt_login(
            username="fantasma4", credential="1234", expected_role=User.Role.ADMIN
        )
        self.assertEqual(mesero_attempt.message, admin_attempt.message)
