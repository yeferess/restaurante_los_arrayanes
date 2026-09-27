from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsAdmin, IsMesero

User = get_user_model()
factory = APIRequestFactory()


class PermissionClassesTests(TestCase):
    """T19 — IsAdmin / IsMesero reject requests whose role does not match (RF-1)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_perm", password="Sup3rSecreta", role=User.Role.ADMIN
        )
        self.mesero = User.objects.create_user(
            username="mesero_perm", password="1234", role=User.Role.MESERO
        )

    def _request_as(self, user):
        request = factory.get("/")
        request.user = user
        return request

    def test_is_admin_allows_admin(self):
        self.assertTrue(IsAdmin().has_permission(self._request_as(self.admin), None))

    def test_is_admin_rejects_mesero(self):
        self.assertFalse(IsAdmin().has_permission(self._request_as(self.mesero), None))

    def test_is_admin_rejects_anonymous(self):
        self.assertFalse(
            IsAdmin().has_permission(self._request_as(AnonymousUser()), None)
        )

    def test_is_mesero_allows_mesero(self):
        self.assertTrue(IsMesero().has_permission(self._request_as(self.mesero), None))

    def test_is_mesero_rejects_admin(self):
        self.assertFalse(IsMesero().has_permission(self._request_as(self.admin), None))

    def test_is_mesero_rejects_anonymous(self):
        self.assertFalse(
            IsMesero().has_permission(self._request_as(AnonymousUser()), None)
        )
