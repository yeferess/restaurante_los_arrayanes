from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsActingOnOwnAdminAccount

User = get_user_model()
factory = APIRequestFactory()


class IsActingOnOwnAdminAccountTests(TestCase):
    """T31 — an admin can only pass the object check for their own account (RF-6)."""

    def setUp(self):
        self.admin_a = User.objects.create_user(
            username="admin_own_a", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.admin_b = User.objects.create_user(
            username="admin_own_b", password="Sup3rSecreta", role=User.Role.ADMIN
        )

    def _request_as(self, user):
        request = factory.post("/")
        request.user = user
        return request

    def test_allows_when_target_is_the_requesting_admin(self):
        request = self._request_as(self.admin_a)
        self.assertTrue(
            IsActingOnOwnAdminAccount().has_object_permission(
                request, None, self.admin_a
            )
        )

    def test_rejects_when_target_is_a_different_admin(self):
        request = self._request_as(self.admin_a)
        self.assertFalse(
            IsActingOnOwnAdminAccount().has_object_permission(
                request, None, self.admin_b
            )
        )
