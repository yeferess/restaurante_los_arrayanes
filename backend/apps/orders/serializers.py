from decimal import Decimal

from rest_framework import serializers

from apps.kitchen_printing.models import PrintJob
from apps.kitchen_printing.rendering import has_unprinted_changes
from apps.orders import services
from apps.orders.grouping import group_items
from apps.orders.models import Order, OrderItem, Table
from apps.payments.models import Payment


class TableSerializer(serializers.ModelSerializer):
    active_order_daily_number = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = ["number", "status", "active_order_daily_number"]

    def get_active_order_daily_number(self, obj):
        """RF-14 (interacción con RF-13): el número del día de un pedido
        no es "contenido" restringido — cualquier mesero autenticado lo
        ve, sea o no el dueño. `None` si la mesa está libre, o si su
        pedido activo todavía no tiene número (caso transitorio)."""
        if obj.status == Table.Status.FREE:
            return None
        target_status = (
            Order.Status.IN_PROGRESS
            if obj.status == Table.Status.OCCUPIED
            else Order.Status.CHARGED
        )
        order = (
            Order.objects.filter(table_number=obj.number, status=target_status)
            .order_by("-created_at")
            .first()
        )
        return order.daily_number if order else None


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.SerializerMethodField()
    pending_send = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order_id",
            "name",
            "unit_price",
            "quantity",
            "note",
            "line_type",
            "is_voided",
            "void_reason",
            "line_total",
            "pending_send",
        ]

    def get_line_total(self, obj):
        """RF-3: quantity × unit price, computed here so no screen does
        the math itself (constitution rule 3)."""
        return str(obj.unit_price * obj.quantity)

    def get_pending_send(self, obj):
        return services.is_pending_send(obj)


def _serialize_groups(items):
    """RF-3: the order's active lines as people read them — the same item
    summed into one line with all its notes — plus the parts each one is
    made of, so a screen can still void or remove exactly one part."""
    return [
        {
            "name": group.name,
            "unit_price": str(group.unit_price),
            "quantity": group.quantity,
            "line_total": str(group.line_total),
            "note": group.note,
            "parts": [
                {
                    "item_id": part.id,
                    "quantity": part.quantity,
                    "line_type": part.line_type,
                    "pending_send": services.is_pending_send(part),
                    "note": part.note,
                }
                for part in group.parts
            ],
        }
        for group in group_items(items)
    ]


def _items_total(items):
    """Active lines that reached the system — never voided ones, never
    additions still unsent (RF-5)."""
    return sum(
        (
            item.unit_price * item.quantity
            for item in items
            if not item.is_voided and not services.is_pending_send(item)
        ),
        Decimal("0.00"),
    )


class OrderSerializer(serializers.ModelSerializer):
    """The waiter's view of their own order: every line, the unsent
    additions flagged `pending_send` and kept out of `total`."""

    items = OrderItemSerializer(many=True, read_only=True)
    item_groups = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    pending_additions_count = serializers.SerializerMethodField()
    pending_additions_total = serializers.SerializerMethodField()
    has_unprinted_changes = serializers.SerializerMethodField()
    has_pending_print = serializers.SerializerMethodField()
    active_payment = serializers.SerializerMethodField()
    waiter_username = serializers.CharField(source="waiter.username", read_only=True)
    draft_reminder = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "table_number",
            "waiter_id",
            "waiter_username",
            "status",
            "delivered",
            "items",
            "item_groups",
            "total",
            "pending_additions_count",
            "pending_additions_total",
            "has_unprinted_changes",
            "has_pending_print",
            "active_payment",
            "daily_number",
            "sent_at",
            "created_at",
            "draft_reminder",
        ]

    def get_item_groups(self, obj):
        """The waiter sees their unsent additions summed in too, flagged
        `pending_send` on their part."""
        return _serialize_groups(obj.items.all())

    def get_total(self, obj):
        return _items_total(obj.items.all())

    def _pending_additions(self, obj):
        return [item for item in obj.items.all() if services.is_pending_send(item)]

    def get_pending_additions_count(self, obj):
        return len(self._pending_additions(obj))

    def get_pending_additions_total(self, obj):
        """RF-5: shown apart ("+ $X sin enviar"), never added to `total`."""
        return str(
            sum(
                (item.unit_price * item.quantity for item in self._pending_additions(obj)),
                Decimal("0.00"),
            )
        )

    def get_has_unprinted_changes(self, obj):
        """004 RF-10: there is something "Imprimir pedido" would print —
        sent changes never on paper, or additions it would send first."""
        if obj.status != Order.Status.IN_PROGRESS:
            return False
        return bool(self._pending_additions(obj)) or has_unprinted_changes(obj)

    def get_draft_reminder(self, obj):
        return services.needs_draft_reminder(obj)

    def get_has_pending_print(self, obj):
        return obj.print_jobs.filter(status=PrintJob.Status.PENDING).exists()

    def get_active_payment(self, obj):
        payment = obj.payments.filter(status=Payment.Status.ACTIVE).first()
        if payment is None:
            return None
        return {
            "account_name": payment.account.name,
            "subtotal": str(payment.subtotal),
            "discount": str(payment.discount),
            "discount_reason": payment.discount_reason,
            "amount": str(payment.amount),
            "charged_by": payment.charged_by.username,
            "charged_at": payment.charged_at.isoformat(),
        }


_WAITER_ONLY_FIELDS = (
    "pending_additions_count",
    "pending_additions_total",
    "has_unprinted_changes",
)


class AdminOrderSerializer(OrderSerializer):
    """RF-17: same payload plus the admin-only note — used exclusively by
    admin-only views so a waiter never receives it. RF-5: only the lines
    that reached the system; an unsent addition stays the waiter's."""

    items = serializers.SerializerMethodField()
    item_groups = serializers.SerializerMethodField()

    class Meta(OrderSerializer.Meta):
        fields = [
            field
            for field in OrderSerializer.Meta.fields
            if field not in _WAITER_ONLY_FIELDS
        ] + ["admin_note"]

    def _sent_items(self, obj):
        return [item for item in obj.items.all() if not services.is_pending_send(item)]

    def get_items(self, obj):
        return OrderItemSerializer(self._sent_items(obj), many=True).data

    def get_item_groups(self, obj):
        return _serialize_groups(self._sent_items(obj))


class OccupiedTableSerializer(serializers.Serializer):
    """RF-15: an occupied table with the order holding it (admin view)."""

    number = serializers.IntegerField()
    order = serializers.SerializerMethodField()
    is_stale = serializers.SerializerMethodField()

    def get_order(self, obj):
        order = services.active_order_for_table(obj.number)
        return AdminOrderSerializer(order).data if order else None

    def get_is_stale(self, obj):
        order = services.active_order_for_table(obj.number)
        return services.is_stale_occupation(order) if order else False
