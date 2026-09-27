from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AdminIsolationFlowTests(APITestCase):
    """T44 — no admin action ever reaches another admin's account (RF-6).

    No endpoint in this module exposes another admin's id as a write
    target (RF-6/RF-10 keep that CLI-only), so this exercises the
    strongest real check available: whatever admin A does through the API
    never touches admin B's username, password or state.
    """

    def setUp(self):
        self.admin_a = User.objects.create_user(
            username="admin_iso_a", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.admin_b = User.objects.create_user(
            username="admin_iso_b", password="OtraSegura9", role=User.Role.ADMIN
        )
        self.client.post(
            "/api/auth/admin/login",
            {"username": "admin_iso_a", "password": "Sup3rSecreta"},
        )

    def test_changing_own_password_never_touches_another_admin(self):
        response = self.client.post(
            "/api/usuarios/admins/me/password",
            {
                "password_actual": "Sup3rSecreta",
                "password_nueva": "NuevaClave9",
                "password_nueva_confirmacion": "NuevaClave9",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.admin_b.refresh_from_db()
        self.assertTrue(self.admin_b.check_password("OtraSegura9"))
        self.assertEqual(self.admin_b.username, "admin_iso_b")
        self.assertTrue(self.admin_b.is_active)

    def test_an_injected_target_id_is_ignored_by_the_serializer(self):
        """Even if a client tries to smuggle another admin's id into the
        body, ChangeOwnPasswordSerializer has no field for it, so it's
        silently dropped and admin B is untouched."""
        response = self.client.post(
            "/api/usuarios/admins/me/password",
            {
                "password_actual": "Sup3rSecreta",
                "password_nueva": "NuevaClave9",
                "password_nueva_confirmacion": "NuevaClave9",
                "target_admin_id": self.admin_b.id,
                "username": "admin_iso_b",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.admin_a.refresh_from_db()
        self.admin_b.refresh_from_db()
        self.assertTrue(self.admin_a.check_password("NuevaClave9"))
        self.assertTrue(self.admin_b.check_password("OtraSegura9"))
        self.assertEqual(self.admin_b.username, "admin_iso_b")

    def test_creating_an_admin_does_not_modify_existing_admins(self):
        response = self.client.post(
            "/api/usuarios/admins", {"username": "admin_iso_c", "password": "TerceraSegura9"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.admin_a.refresh_from_db()
        self.admin_b.refresh_from_db()
        self.assertTrue(self.admin_a.check_password("Sup3rSecreta"))
        self.assertTrue(self.admin_b.check_password("OtraSegura9"))
