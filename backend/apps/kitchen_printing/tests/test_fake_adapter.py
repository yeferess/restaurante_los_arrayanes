from unittest import TestCase

from apps.kitchen_printing.adapters import PrinterFailureError, PrinterNotDetectedError
from apps.kitchen_printing.fake_adapter import FakePrinterAdapter


class FakePrinterAdapterTests(TestCase):
    """T05 — FakePrinterAdapter, the test double for every automated
    test in this module (RF-9 support)."""

    def test_succeeds_by_default_and_records_the_exact_text(self):
        adapter = FakePrinterAdapter()
        adapter.print_ticket("hola mundo")
        self.assertEqual(adapter.call_count, 1)
        self.assertEqual(adapter.printed_texts, ["hola mundo"])

    def test_can_be_configured_to_raise_not_detected(self):
        adapter = FakePrinterAdapter(fail_with=PrinterNotDetectedError)
        with self.assertRaises(PrinterNotDetectedError):
            adapter.print_ticket("algo")
        self.assertEqual(adapter.call_count, 1)

    def test_can_be_configured_to_raise_print_failure(self):
        adapter = FakePrinterAdapter(fail_with=PrinterFailureError)
        with self.assertRaises(PrinterFailureError):
            adapter.print_ticket("algo")

    def test_counts_every_call_even_across_failures_and_successes(self):
        adapter = FakePrinterAdapter(fail_with=PrinterFailureError)
        with self.assertRaises(PrinterFailureError):
            adapter.print_ticket("intento 1")
        adapter.fail_with = None
        adapter.print_ticket("intento 2")
        self.assertEqual(adapter.call_count, 2)
        self.assertEqual(adapter.printed_texts, ["intento 2"])
