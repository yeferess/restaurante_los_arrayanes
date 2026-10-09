from django.test import TestCase, override_settings

from apps.kitchen_printing.factory import get_printer_adapter
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter


class GetPrinterAdapterTests(TestCase):
    """T06 — get_printer_adapter() factory and settings (RF-9 support,
    regla 1 de la constitución)."""

    @override_settings(KITCHEN_PRINTER_ADAPTER="fake")
    def test_returns_the_fake_adapter_when_settings_say_fake(self):
        adapter = get_printer_adapter()
        self.assertIsInstance(adapter, FakePrinterAdapter)

    @override_settings(KITCHEN_PRINTER_ADAPTER="escpos")
    def test_returns_the_real_adapter_when_settings_say_escpos(self):
        from apps.kitchen_printing.escpos_adapter import EscposUsbPrinterAdapter

        with self._patched_win32print():
            adapter = get_printer_adapter()
        self.assertIsInstance(adapter, EscposUsbPrinterAdapter)

    @staticmethod
    def _patched_win32print():
        from unittest.mock import patch

        return patch("apps.kitchen_printing.escpos_adapter.win32print")

    def test_settings_define_the_printer_columns(self):
        from django.conf import settings

        self.assertEqual(settings.KITCHEN_PRINTER_COLUMNS, 40)
