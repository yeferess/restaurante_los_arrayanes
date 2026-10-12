import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders import services
from apps.orders.models import Order, OrderItem, Table
from apps.orders.permissions import IsAdmin, IsMesero
from apps.orders.serializers import (
    AdminOrderSerializer,
    OccupiedTableSerializer,
    OrderItemSerializer,
    OrderSerializer,
    TableSerializer,
)
from apps.payments.models import Payment


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


def _day_from_query(request):
    """`?fecha=YYYY-MM-DD` as a date (today, local, when omitted)."""
    raw_date = request.query_params.get("fecha")
    if not raw_date:
        return timezone.localdate(), None
    try:
        return datetime.date.fromisoformat(raw_date), None
    except ValueError:
        return None, Response(
            {"detail": ["La fecha debe tener el formato AAAA-MM-DD."]},
            status=status.HTTP_400_BAD_REQUEST,
        )


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
        services.discard_stale_drafts()
        tables = Table.objects.order_by("number")
        return Response(TableSerializer(tables, many=True).data)


class OccupiedTablesView(APIView):
    """GET /api/mesas/ocupadas (RF-15). Admin-only: each occupied table
    with the order holding it, so a forgotten one can be voided."""

    permission_classes = [IsAdmin]

    def get(self, request):
        services.discard_stale_drafts()
        tables = Table.objects.filter(status=Table.Status.OCCUPIED).order_by("number")
        return Response(OccupiedTableSerializer(tables, many=True).data)


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
        day, error = _day_from_query(request)
        if error:
            return error
        services.discard_stale_drafts()
        orders = services.my_orders_for_day(request.user, day)
        return Response(OrderSerializer(orders, many=True).data)


class IncomingOrdersView(APIView):
    """GET /api/pedidos/entrantes (soporta RF-9, RF-11). Admin-only."""

    permission_classes = [IsAdmin]

    def get(self, request):
        orders = Order.objects.filter(status=Order.Status.IN_PROGRESS).order_by(
            "created_at"
        )
        return Response(AdminOrderSerializer(orders, many=True).data)


class ChargedOrdersView(APIView):
    """GET /api/pedidos/cobrados?fecha=YYYY-MM-DD (005 RF-9). Admin-only.
    Orders charged on that local date (today when omitted), newest
    charge first — the admin's "Cobrados" tab, from where they can be
    reprinted (004 RF-12)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        day, error = _day_from_query(request)
        if error:
            return error

        active_charged_at = Payment.objects.filter(
            order=OuterRef("pk"), status=Payment.Status.ACTIVE
        ).values("charged_at")[:1]
        orders = (
            Order.objects.filter(status=Order.Status.CHARGED)
            .annotate(charged_at=Subquery(active_charged_at))
            .filter(charged_at__date=day)
            .order_by("-charged_at")
        )
        return Response(AdminOrderSerializer(orders, many=True).data)


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

        serializer_class = AdminOrderSerializer if is_admin else OrderSerializer
        return Response(serializer_class(order).data)

    def delete(self, request, pk):
        order, error = _get_own_order_or_error(request, pk)
        if error:
            return error
        try:
            services.delete_order(order)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        data = OrderItemSerializer(item).data
        data["print_warning"] = getattr(order, "print_warning", None)
        return Response(data, status=status.HTTP_201_CREATED)


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
        data = OrderItemSerializer(item).data
        data["print_warning"] = getattr(order, "print_warning", None)
        return Response(data)


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
        data = OrderSerializer(order).data
        data["print_warning"] = getattr(order, "print_warning", None)
        return Response(data)


class ChargeOrderView(APIView):
    """POST /api/pedidos/{id}/cobrar (005-cobro, RF-1, RF-3, RF-5, RF-10).
    Admin-only; `discount` (pesos) and `discount_reason` are optional."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        from apps.payments.models import PaymentAccount
        from apps.payments.services import charge_order

        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            account = PaymentAccount.objects.get(pk=request.data.get("account_id"))
        except (PaymentAccount.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "account_id es obligatorio y debe ser una cuenta válida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            charge_order(
                order,
                request.user,
                account,
                discount=request.data.get("discount"),
                discount_reason=request.data.get("discount_reason", ""),
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=(
                    status.HTTP_400_BAD_REQUEST
                    if exc.code == "invalid"
                    else status.HTTP_409_CONFLICT
                ),
            )
        data = AdminOrderSerializer(order).data
        return Response(data)


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
        return Response(AdminOrderSerializer(order).data)


class DiscardDraftView(APIView):
    """POST /api/pedidos/{id}/eliminar-borrador (RF-15). Admin-only:
    one-click void of a draft with a fixed reason (RF-11/RF-12)."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            services.discard_draft_by_admin(order, request.user)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_409_CONFLICT
            )
        return Response(AdminOrderSerializer(order).data)


class AdminNoteView(APIView):
    """PATCH /api/pedidos/{id}/nota-admin (RF-17). Admin-only."""

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            services.set_admin_note(order, request.data.get("note", ""))
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(AdminOrderSerializer(order).data)


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
