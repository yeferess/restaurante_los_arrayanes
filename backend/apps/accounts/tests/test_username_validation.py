from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

User = get_user_model()


class UsernameValidationTests(TestCase):
    """T08 — username format and global case-insensitive uniqueness (RF-2)."""

    def test_username_too_short_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(username="ab", password="1234", role=User.Role.MESERO)

    def test_username_too_long_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="a" * 21, password="1234", role=User.Role.MESERO
            )

    def test_username_with_spaces_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="juan perez", password="1234", role=User.Role.MESERO
            )

    def test_username_with_symbols_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="juan!perez", password="1234", role=User.Role.MESERO
            )

    def test_username_with_letters_numbers_and_underscore_is_accepted(self):
        user = User.objects.create_user(
            username="juan_p3rez", password="1234", role=User.Role.MESERO
        )
        self.assertEqual(user.username, "juan_p3rez")

    def test_username_is_normalized_to_lowercase(self):
        user = User.objects.create_user(
            username="JuanPerez1", password="1234", role=User.Role.MESERO
        )
        self.assertEqual(user.username, "juanperez1")

    def test_duplicate_username_case_insensitive_is_rejected(self):
        User.objects.create_user(
            username="carlos_m", password="1234", role=User.Role.MESERO
        )
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="Carlos_M", password="5678", role=User.Role.MESERO
            )

    def test_duplicate_is_rejected_across_roles(self):
        User.objects.create_user(
            username="ana_admin2", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                username="ana_admin2", password="5678", role=User.Role.MESERO
            )
