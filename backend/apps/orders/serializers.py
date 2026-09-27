from decimal import Decimal

from rest_framework import serializers

from apps.orders.models import Order, OrderItem, Table


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ["number", "status"]


class OrderItemSerializer(serializers.ModelSerializer):
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
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "table_number",
            "waiter_id",
            "status",
            "delivered",
            "items",
            "total",
        ]

    def get_total(self, obj):
        return sum(
            (item.unit_price * item.quantity for item in obj.items.all() if not item.is_voided),
            Decimal("0.00"),
        )
