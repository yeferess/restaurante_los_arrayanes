from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.services import attempt_login

User = get_user_model()


class DifferentiatedMessagesTests(TestCase):
    """T15 — the 5 exact RF-1 messages, one per role/state scenario."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_msg", password="1234", role=User.Role.MESERO
        )
        self.admin = User.objects.create_user(
            username="admin_msg", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def test_locked_mesero_message(self):
        self.mesero.is_locked = True
        self.mesero.save(update_fields=["is_locked"])
        result = attempt_login(
            username="mesero_msg", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertEqual(
            result.message,
            "Tu cuenta está bloqueada. Habla con un administrador para resolverlo.",
        )

    def test_locked_admin_message(self):
        self.admin.is_locked = True
        self.admin.save(update_fields=["is_locked"])
        result = attempt_login(
            username="admin_msg", credential="Sup3rSecreta", expected_role=User.Role.ADMIN
        )
        self.assertEqual(
            result.message,
            "Tu cuenta está bloqueada. Espera 20 minutos o contacta al "
            "operador técnico del sistema.",
        )

    def test_deactivated_mesero_message(self):
        self.mesero.is_active = False
        self.mesero.save(update_fields=["is_active"])
        result = attempt_login(
            username="mesero_msg", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertEqual(
            result.message,
            "Tu cuenta está desactivada. Habla con un administrador para resolverlo.",
        )

    def test_deactivated_admin_message(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        result = attempt_login(
            username="admin_msg", credential="Sup3rSecreta", expected_role=User.Role.ADMIN
        )
        self.assertEqual(
            result.message,
            "Tu cuenta fue desactivada permanentemente. Contacta al "
            "operador técnico si necesitas una cuenta nueva.",
        )

    def test_invalid_credentials_message_shows_remaining_attempts(self):
        result = attempt_login(
            username="mesero_msg", credential="wrong", expected_role=User.Role.MESERO
        )
        self.assertEqual(
            result.message,
            "Usuario o contraseña incorrectos. Te quedan 4 intentos antes del bloqueo.",
        )
