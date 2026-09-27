from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsAdmin as AccountsIsAdmin
from apps.accounts.permissions import IsMesero as AccountsIsMesero
from apps.menu.permissions import IsAdmin, IsMesero


class MenuPermissionsReuseTests(TestCase):
    """T14 — reuse apps.accounts.permissions instead of duplicating it (RF-8)."""

    def test_is_admin_is_the_same_class_as_accounts(self):
        self.assertIs(IsAdmin, AccountsIsAdmin)

    def test_is_mesero_is_the_same_class_as_accounts(self):
        self.assertIs(IsMesero, AccountsIsMesero)

    def test_is_admin_rejects_a_request_without_an_authenticated_user(self):
        request = APIRequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertFalse(IsAdmin().has_permission(Request(request), None))

    def test_is_mesero_rejects_a_request_without_an_authenticated_user(self):
        request = APIRequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertFalse(IsMesero().has_permission(Request(request), None))
