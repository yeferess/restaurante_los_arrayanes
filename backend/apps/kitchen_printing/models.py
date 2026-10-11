from django.db import models

from apps.orders.models import Order


class PrintJob(models.Model):
    """Tracks the single pending kitchen ticket for an order, if any
    (RF-8, RF-9, RF-10). Never stores the ticket's rendered text — the
    content is always regenerated from the order's current state (see
    apps.kitchen_printing.rendering), never a frozen snapshot.
    """

    class TicketType(models.TextChoices):
        NEW_ORDER = "NEW_ORDER", "New order"
        ADDITION = "ADDITION", "Addition"
        VOID = "VOID", "Void"
        # A manual copy of the whole order (RF-12). Never PENDING, and never
        # used as the "already on paper" reference for the next ticket.
        REPRINT = "REPRINT", "Reprint"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PRINTED = "PRINTED", "Printed"

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="print_jobs"
    )
    ticket_type = models.CharField(max_length=9, choices=TicketType.choices)
    status = models.CharField(
        max_length=7, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    printed_at = models.DateTimeField(null=True, blank=True)
    # High-water marks: the last OrderItem/OrderAction id already shown on
    # paper as of this job's successful print. Comparing by id (strictly
    # sequential, never tied) instead of by timestamp avoids false
    # inclusion/exclusion when two rows are created in the same instant.
    last_item_id = models.PositiveIntegerField(null=True, blank=True)
    last_action_id = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.ticket_type} ticket for order {self.order_id} ({self.status})"
