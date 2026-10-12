from decimal import Decimal

from rest_framework import serializers

from apps.kitchen_printing.models import PrintJob
from apps.orders import services
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
        ]

    def get_line_total(self, obj):
        """RF-3: quantity × unit price, computed here so no screen does
        the math itself (constitution rule 3)."""
        return str(obj.unit_price * obj.quantity)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
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
            "total",
            "has_pending_print",
            "active_payment",
            "daily_number",
            "sent_at",
            "created_at",
            "draft_reminder",
        ]

    def get_total(self, obj):
        return sum(
            (item.unit_price * item.quantity for item in obj.items.all() if not item.is_voided),
            Decimal("0.00"),
        )

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


class AdminOrderSerializer(OrderSerializer):
    """RF-17: same payload plus the admin-only note — used exclusively by
    admin-only views so a waiter never receives it."""

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["admin_note"]


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
