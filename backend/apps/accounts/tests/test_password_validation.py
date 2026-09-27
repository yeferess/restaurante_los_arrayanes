from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

User = get_user_model()


class MeseroPinValidationTests(TestCase):
    """T09 — mesero PIN must be 4-6 numeric digits (RF-2)."""

    def test_pin_with_3_digits_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="mesero_pin1", password="123", role=User.Role.MESERO
            )

    def test_pin_with_7_digits_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="mesero_pin2", password="1234567", role=User.Role.MESERO
            )

    def test_non_numeric_pin_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="mesero_pin3", password="12ab", role=User.Role.MESERO
            )

    def test_pin_with_4_to_6_digits_is_accepted(self):
        for pin in ("1234", "12345", "123456"):
            with self.subTest(pin=pin):
                user = User.objects.create_user(
                    username=f"mesero_pin_{pin}", password=pin, role=User.Role.MESERO
                )
                self.assertTrue(user.check_password(pin))


class AdminPasswordValidationTests(TestCase):
    """T09 — admin password: 8+ chars, letters and digits combined (RF-6, RF-10)."""

    def test_password_shorter_than_8_chars_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="admin_pw1", password="Abc123!", role=User.Role.ADMIN
            )

    def test_password_without_digits_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="admin_pw2", password="SoloLetras", role=User.Role.ADMIN
            )

    def test_password_without_letters_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="admin_pw3", password="12345678", role=User.Role.ADMIN
            )

    def test_valid_admin_password_is_accepted(self):
        user = User.objects.create_user(
            username="admin_pw4", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.assertTrue(user.check_password("Sup3rSecreta"))
