from django.apps import apps
from django.test import SimpleTestCase


class AccountsAppConfigTests(SimpleTestCase):
    """T01 — the accounts app must exist and be registered."""

    def test_accounts_app_is_installed(self):
        self.assertTrue(apps.is_installed("apps.accounts"))

    def test_accounts_app_config_name(self):
        config = apps.get_app_config("accounts")
        self.assertEqual(config.name, "apps.accounts")
