from unittest import TestCase

from apps.kitchen_printing.adapters import (
    PrinterAdapter,
    PrinterError,
    PrinterFailureError,
    PrinterNotDetectedError,
)


class PrinterAdapterInterfaceTests(TestCase):
    """T04 — PrinterAdapter interface and its two failure categories
    (RF-9: "impresora no detectada" vs. "error al imprimir")."""

    def test_printer_adapter_cannot_be_instantiated_directly(self):
        with self.assertRaises(TypeError):
            PrinterAdapter()

    def test_a_concrete_adapter_must_implement_print_ticket(self):
        class IncompleteAdapter(PrinterAdapter):
            pass

        with self.assertRaises(TypeError):
            IncompleteAdapter()

    def test_a_concrete_adapter_implementing_print_ticket_can_be_instantiated(self):
        class ConcreteAdapter(PrinterAdapter):
            def print_ticket(self, text):
                pass

        ConcreteAdapter().print_ticket("hola")

    def test_the_two_failure_exceptions_share_a_common_base(self):
        self.assertTrue(issubclass(PrinterNotDetectedError, PrinterError))
        self.assertTrue(issubclass(PrinterFailureError, PrinterError))
