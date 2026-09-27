from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders import services
from apps.orders.models import Order, OrderItem, Table
from apps.orders.permissions import IsAdmin, IsMesero
from apps.orders.serializers import OrderItemSerializer, OrderSerializer, TableSerializer


def _status_for(exc):
    return (
        status.HTTP_409_CONFLICT
        if exc.code == "not_free"
        else status.HTTP_400_BAD_REQUEST
    )


def _item_status_for(exc):
    if exc.code == "not_found":
        return status.HTTP_404_NOT_FOUND
    if exc.code in ("not_available", "not_editable"):
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


def _parse_price(raw):
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return raw


def _get_own_order_or_error(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return None, Response(status=status.HTTP_404_NOT_FOUND)
    if order.waiter_id != request.user.id:
        return None, Response(status=status.HTTP_403_FORBIDDEN)
    return order, None


class TableListView(APIView):
    """GET /api/mesas (RF-1, RF-13). Any authenticated account."""

    def get(self, request):
        tables = Table.objects.order_by("number")
        return Response(TableSerializer(tables, many=True).data)


class ResizeTablesView(APIView):
    """PATCH /api/mesas/numero (RF-1). Admin-only."""

    permission_classes = [IsAdmin]

    def patch(self, request):
        try:
            new_count = int(request.data.get("numero"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "El número de mesas debe ser un entero."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tables = services.resize_tables(new_count)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(TableSerializer(tables, many=True).data)


class ReleaseTableView(APIView):
    """POST /api/mesas/{numero}/liberar (RF-10). Any mesero."""

    permission_classes = [IsMesero]

    def post(self, request, numero):
        try:
            table = services.release_table(numero)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=(
                    status.HTTP_404_NOT_FOUND
                    if exc.code == "invalid"
                    else status.HTTP_409_CONFLICT
                ),
            )
        return Response(TableSerializer(table).data)


class CreateOrderView(APIView):
    """POST /api/pedidos (RF-2). Mesero-only."""

    permission_classes = [IsMesero]

    def post(self, request):
        try:
            table_number = int(request.data.get("table_number"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "table_number es obligatorio y debe ser un entero."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order = services.create_order(request.user, table_number)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class MyOrdersView(APIView):
    """GET /api/pedidos/mios (RF-8, RF-10, RF-13). Mesero-only, own
    orders."""

    permission_classes = [IsMesero]

    def get(self, request):
        orders = Order.objects.filter(waiter=request.user).order_by("-created_at")
        return Response(OrderSerializer(orders, many=True).data)


class IncomingOrdersView(APIView):
    """GET /api/pedidos/entrantes (soporta RF-9, RF-11). Admin-only."""

    permission_classes = [IsAdmin]

    def get(self, request):
        orders = Order.objects.filter(status=Order.Status.IN_PROGRESS).order_by(
            "created_at"
        )
        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    """GET /api/pedidos/{id} (RF-13). The owner or an admin."""

    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_admin = request.user.role == request.user.Role.ADMIN
        is_owner = order.waiter_id == request.user.id
        if not (is_admin or is_owner):
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(OrderSerializer(order).data)


class AddItemView(APIView):
    """POST /api/pedidos/{id}/items (RF-3, RF-4, RF-5). Owner-only."""

    permission_classes = [IsMesero]

    def post(self, request, pk):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error

        data = request.data
        try:
            item = services.add_item(
                order,
                product_id=data.get("product_id"),
                name=data.get("name"),
                price=_parse_price(data.get("price")),
                quantity=int(data.get("quantity", 1)),
                note=data.get("note", ""),
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_item_status_for(exc))
        return Response(
            OrderItemSerializer(item).data, status=status.HTTP_201_CREATED
        )


class RemoveItemView(APIView):
    """DELETE /api/pedidos/{id}/items/{item_id} (RF-2). Owner-only."""

    permission_classes = [IsMesero]

    def delete(self, request, pk, item_id):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error
        try:
            item = order.items.get(pk=item_id)
        except OrderItem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            services.remove_item(order, item)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VoidItemView(APIView):
    """POST /api/pedidos/{id}/items/{item_id}/anular (RF-6). Owner-only."""

    permission_classes = [IsMesero]

    def post(self, request, pk, item_id):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error
        try:
            item = order.items.get(pk=item_id)
        except OrderItem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason")
        if not reason:
            return Response(
                {"detail": "El motivo es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            services.void_item(order, item, request.user, reason)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(OrderItemSerializer(item).data)


class SendOrderView(APIView):
    """POST /api/pedidos/{id}/enviar (RF-5). Owner-only."""

    permission_classes = [IsMesero]

    def post(self, request, pk):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error
        try:
            services.send_order(order)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(OrderSerializer(order).data)


class ChargeOrderView(APIView):
    """POST /api/pedidos/{id}/cobrar (RF-9). Admin-only."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            services.charge_order(order, request.user)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(OrderSerializer(order).data)


class VoidOrderView(APIView):
    """POST /api/pedidos/{id}/anular (RF-11). Admin-only."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason")
        if not reason:
            return Response(
                {"detail": "El motivo es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            services.void_order(order, request.user, reason)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(OrderSerializer(order).data)


class SetDeliveredView(APIView):
    """POST /api/pedidos/{id}/entregado (RF-8). Owner-only."""

    permission_classes = [IsMesero]

    def post(self, request, pk):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error
        try:
            services.set_delivered(order, bool(request.data.get("delivered")))
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(OrderSerializer(order).data)


class FixTableView(APIView):
    """POST /api/pedidos/{id}/mesa (RF-7). Owner-only."""

    permission_classes = [IsMesero]

    def post(self, request, pk):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error
        try:
            new_table_number = int(request.data.get("table_number"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "table_number es obligatorio y debe ser un entero."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            services.fix_table(order, request.user, new_table_number)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_status_for(exc))
        return Response(OrderSerializer(order).data)


class UpdateItemNoteView(APIView):
    """PATCH /api/pedidos/{id}/items/{item_id}/nota (RF-4). Owner-only."""

    permission_classes = [IsMesero]

    def patch(self, request, pk, item_id):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error
        try:
            item = order.items.get(pk=item_id)
        except OrderItem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            services.update_item_note(item, request.data.get("note", ""))
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=_item_status_for(exc))
        return Response(OrderItemSerializer(item).data)
