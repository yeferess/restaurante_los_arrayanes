from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    """T03 — base User model (username, role, hashed password, is_active)."""

    def test_create_user_hashes_password(self):
        user = User.objects.create_user(
            username="ana_admin", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.assertNotEqual(user.password, "Sup3rSecreta")
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password("Sup3rSecreta"))
        self.assertFalse(user.check_password("wrong-password"))

    def test_user_defaults_to_active(self):
        user = User.objects.create_user(
            username="carlos_m", password="1234", role=User.Role.MESERO
        )
        self.assertTrue(user.is_active)

    def test_role_choices(self):
        field = User._meta.get_field("role")
        self.assertEqual(
            {value for value, _ in field.choices}, {"ADMIN", "MESERO"}
        )

    def test_username_is_the_natural_key(self):
        self.assertEqual(User.USERNAME_FIELD, "username")

    def test_username_must_be_unique(self):
        User.objects.create_user(
            username="unico", password="1234", role=User.Role.MESERO
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                username="unico", password="5678", role=User.Role.MESERO
            )


class UserLockoutFieldsTests(TestCase):
    """T04 — lockout bookkeeping fields (RF-7)."""

    def test_user_defaults_to_unlocked(self):
        user = User.objects.create_user(
            username="mesero_lock", password="1234", role=User.Role.MESERO
        )
        self.assertFalse(user.is_locked)

    def test_locked_at_defaults_to_none(self):
        user = User.objects.create_user(
            username="mesero_lock2", password="1234", role=User.Role.MESERO
        )
        self.assertIsNone(user.locked_at)

    def test_failed_login_attempts_defaults_to_zero(self):
        user = User.objects.create_user(
            username="mesero_lock3", password="1234", role=User.Role.MESERO
        )
        self.assertEqual(user.failed_login_attempts, 0)


class UserSessionAndAuditFieldsTests(TestCase):
    """T05 — current_session_key (RF-9) and created_by (RF-2, RF-6, RF-11)."""

    def test_current_session_key_defaults_to_none(self):
        user = User.objects.create_user(
            username="mesero_sess", password="1234", role=User.Role.MESERO
        )
        self.assertIsNone(user.current_session_key)

    def test_created_by_defaults_to_none(self):
        admin = User.objects.create_user(
            username="admin_root", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.assertIsNone(admin.created_by)

    def test_created_by_references_another_user(self):
        admin = User.objects.create_user(
            username="admin_creator", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        mesero = User.objects.create_user(
            username="mesero_creado",
            password="1234",
            role=User.Role.MESERO,
            created_by=admin,
        )
        self.assertEqual(mesero.created_by, admin)

    def test_created_by_protects_creator_from_deletion(self):
        admin = User.objects.create_user(
            username="admin_protegido", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        User.objects.create_user(
            username="mesero_dependiente",
            password="1234",
            role=User.Role.MESERO,
            created_by=admin,
        )
        with self.assertRaises(ProtectedError):
            admin.delete()
