from django.conf import settings
from django.db import models


class Table(models.Model):
    """Restaurant table (RF-1). `number` is a plain field, not the PK,
    because resizing the table count creates/deletes rows by exact
    numbering (see plan.md, section 5, decision 1)."""

    class Status(models.TextChoices):
        FREE = "FREE", "Free"
        OCCUPIED = "OCCUPIED", "Occupied"
        PAID = "PAID", "Paid"

    number = models.PositiveIntegerField(unique=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.FREE
    )

    def __str__(self):
        return f"Table {self.number}"


class Order(models.Model):
    """A table's active/finished order (RF-2, RF-5, RF-8, RF-9, RF-11).

    `table_number` is a plain copy of the table's number at creation
    time (or after RF-7's correction) — never a live FK to `Table`, so
    resizing the table count never breaks historical orders (see
    plan.md, section 5, decision 1). Empty for a counter / takeaway
    order ("Mostrador", RF-18), which never holds a table.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        CHARGED = "CHARGED", "Charged"
        VOIDED = "VOIDED", "Voided"

    table_number = models.PositiveIntegerField(null=True, blank=True)
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=11, choices=Status.choices, default=Status.DRAFT
    )
    delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    daily_number = models.PositiveIntegerField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    # RF-17: free-text note only the admin writes and sees — never sent
    # to waiters, the kitchen ticket or the customer receipt.
    admin_note = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"Order {self.id} ({table_label(self)})"


def table_label(order):
    """RF-18: how an order's place reads on screens, tickets and receipts —
    "Mesa N", or "Mostrador" for a counter order without a table."""
    if order.table_number is None:
        return "Mostrador"
    return f"Mesa {order.table_number}"


class OrderItem(models.Model):
    """A single line of an order (RF-3, RF-4, RF-5, RF-6).

    `catalog_product` is optional and only for reporting — `name` and
    `unit_price` are always the copied/frozen values actually used to
    compute totals, never re-read from the product (same snapshot
    pattern as 002-gestion-menu's order-line design).
    """

    class LineType(models.TextChoices):
        ORIGINAL = "ORIGINAL", "Original"
        ADDITION = "ADDITION", "Addition"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    catalog_product = models.ForeignKey(
        "menu.Product", null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    # RF-4: one line per note — a repeated item merged into this line
    # (RF-3) adds its note as a new line underneath.
    note = models.TextField(blank=True)
    line_type = models.CharField(
        max_length=8, choices=LineType.choices, default=LineType.ORIGINAL
    )
    is_voided = models.BooleanField(default=False)
    void_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # RF-5: when the line reached the system (the admin, the total, the
    # kitchen). Empty while still in a draft, or for an addition the
    # waiter hasn't sent yet — that one stays private to the waiter.
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.name} (order {self.order_id})"


class OrderAction(models.Model):
    """Audit trail for sensitive order actions (RF-12, constitution rule 4).

    A single table centralizes item voids, order voids (manual or
    automatic), table corrections and charges — same pattern as
    `AccountAction` in 001-autenticacion-usuarios. `TABLE_CORRECTED` rows
    double as the "mesa change history" for an order.
    """

    class ActionType(models.TextChoices):
        ITEM_VOIDED = "ITEM_VOIDED", "Item voided"
        ORDER_VOIDED = "ORDER_VOIDED", "Order voided"
        ORDER_VOIDED_AUTO = "ORDER_VOIDED_AUTO", "Order voided automatically"
        TABLE_CORRECTED = "TABLE_CORRECTED", "Table corrected"
        CHARGED = "CHARGED", "Charged"

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="actions"
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="order_actions"
    )
    reason = models.TextField(null=True, blank=True)
    item = models.ForeignKey(
        OrderItem, null=True, blank=True, on_delete=models.PROTECT
    )
    from_table_number = models.PositiveIntegerField(null=True, blank=True)
    to_table_number = models.PositiveIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} on order {self.order_id} @ {self.timestamp}"


class DailyOrderCounter(models.Model):
    """Per-local-date sequence for `Order.daily_number` (RF-14). One row
    per day, created lazily the first time an order is sent that day —
    see apps/orders/services.py for how it's incremented under a lock."""

    local_date = models.DateField(primary_key=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.local_date}: {self.last_number}"
