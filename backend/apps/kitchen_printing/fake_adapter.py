from apps.kitchen_printing.adapters import PrinterAdapter


class FakePrinterAdapter(PrinterAdapter):
    """Test double for PrinterAdapter — stands in for the real Epson
    TM-U220 in every automated test (plan.md, section 1/8)."""

    def __init__(self, fail_with=None):
        self.fail_with = fail_with
        self.call_count = 0
        self.printed_texts = []

    def print_ticket(self, text: str, doc_name: str = "Ticket de cocina") -> None:
        self.call_count += 1
        if self.fail_with is not None:
            raise self.fail_with("Fallo simulado por FakePrinterAdapter.")
        self.printed_texts.append(text)
