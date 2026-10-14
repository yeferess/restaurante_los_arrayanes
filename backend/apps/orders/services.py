"""Pure business logic for the orders module (RF-1..RF-13).

Kept free of HTTP/request concerns so it can be unit tested directly
(see specs/003-mesas-pedidos/plan.md, sections 1 and 6).
"""

import threading
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.menu.models import Product
from apps.orders.consumers import ORDERS_GROUP_NAME
from apps.orders.models import DailyOrderCounter, Order, OrderAction, OrderItem, Table

ITEM_NAME_MAX_LENGTH = 100
NOTE_MAX_LENGTH = 200
# RF-4: cap for a line's merged notes (several repeated items, RF-3).
MERGED_NOTE_MAX_LENGTH = 1000
ADMIN_NOTE_MAX_LENGTH = 300

# RF-15: thresholds that keep a forgotten order from holding a table.
EMPTY_DRAFT_TTL = timedelta(minutes=10)
DRAFT_REMINDER_AFTER = timedelta(minutes=15)
STALE_TABLE_AFTER = timedelta(hours=3)
DRAFT_DISCARD_REASON = "Borrador eliminado por el admin"

# RF-14: a single process-wide lock serializes the read-increment-save
# cycle on DailyOrderCounter, same pattern already used by
# kitchen_printing's _print_lock for its own single shared resource —
# see specs/003-mesas-pedidos/plan.md, sección 4.1.
_daily_number_lock = threading.Lock()


def _assign_daily_number(order):
    """RF-14: assign (daily_number, sent_at) exactly once. Must be
    called before order.save() inside the same transaction as the rest
    of send_order's changes, so a failure rolls back both together."""
    with _daily_number_lock:
        local_date = timezone.localdate()
        counter, _ = DailyOrderCounter.objects.get_or_create(
            local_date=local_date, defaults={"last_number": 0}
        )
        counter.last_number += 1
        counter.save(update_fields=["last_number"])
        order.daily_number = counter.last_number
        order.sent_at = timezone.now()


def notify_orders_changed():
    """RF-6 (plan, sección 4): notify the admin panel that an order
    changed. Call sites already match the scope decided in plan.md
    (notifies from sending an order onward, never for a private draft).
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        ORDERS_GROUP_NAME, {"type": "pedidos.actualizado"}
    )


def resize_tables(new_count):
    """RF-1: set the total number of tables to `new_count` (1..N)."""
    if new_count < 1:
        raise ValidationError("Debe haber al menos 1 mesa.", code="invalid")

    current_count = Table.objects.count()
    if new_count > current_count:
        Table.objects.bulk_create(
            [Table(number=n) for n in range(current_count + 1, new_count + 1)]
        )
    elif new_count < current_count:
        to_remove = Table.objects.filter(number__gt=new_count)
        if to_remove.exclude(status=Table.Status.FREE).exists():
            raise ValidationError(
                "Alguna de las mesas a eliminar no está libre.", code="not_free"
            )
        to_remove.delete()
    return Table.objects.order_by("number")


def discard_stale_drafts():
    """RF-15: delete drafts left without a single item for longer than
    EMPTY_DRAFT_TTL, and every draft from a previous local day (items or
    not), freeing their tables — same "no trace" deletion as
    delete_order. Called lazily from the reads/creates that would
    otherwise see the table as occupied."""
    drafts = Order.objects.filter(status=Order.Status.DRAFT)
    stale = drafts.filter(
        created_at__lte=timezone.now() - EMPTY_DRAFT_TTL, items__isnull=True
    ) | drafts.filter(created_at__date__lt=timezone.localdate())
    for order in stale.distinct():
        _free_table(order.table_number)
        order.delete()


def my_orders_for_day(waiter, day):
    """RF-16: the waiter's orders created on `day` (local). For today,
    also the still-pending ones from earlier days: in progress, or the
    latest charged order of a table that is still paid (to release it)."""
    orders = Order.objects.filter(waiter=waiter)
    selected = orders.filter(created_at__date=day)
    if day == timezone.localdate():
        earlier = orders.filter(created_at__date__lt=day)
        carried_ids = list(
            earlier.filter(status=Order.Status.IN_PROGRESS).values_list("id", flat=True)
        )
        paid_tables = Table.objects.filter(status=Table.Status.PAID).values_list(
            "number", flat=True
        )
        for number in paid_tables:
            latest_charged = (
                Order.objects.filter(table_number=number, status=Order.Status.CHARGED)
                .order_by("-created_at")
                .first()
            )
            if latest_charged and latest_charged.waiter_id == waiter.id:
                carried_ids.append(latest_charged.id)
        selected = selected | orders.filter(id__in=carried_ids)
    return selected.distinct().order_by("-created_at")


def needs_draft_reminder(order):
    """RF-15: a draft with items that has gone unsent for too long."""
    return (
        order.status == Order.Status.DRAFT
        and order.created_at <= timezone.now() - DRAFT_REMINDER_AFTER
        and order.items.exists()
    )


def active_order_for_table(table_number):
    """RF-2: the single draft/in-progress order holding a table, if any."""
    return (
        Order.objects.filter(
            table_number=table_number,
            status__in=(Order.Status.DRAFT, Order.Status.IN_PROGRESS),
        )
        .order_by("-created_at")
        .first()
    )


def is_stale_occupation(order):
    """RF-15: the table has been held by this order for too long."""
    return order.created_at <= timezone.now() - STALE_TABLE_AFTER


def create_order(waiter, table_number):
    """RF-2: create a draft order on a free table. RF-18: an admin may
    pass `table_number=None` for a counter order ("Mostrador"), which
    holds no table."""
    discard_stale_drafts()
    if table_number is None:
        if waiter.role != waiter.Role.ADMIN:
            raise ValidationError("Debes elegir una mesa.", code="invalid")
        return Order.objects.create(table_number=None, waiter=waiter)
    try:
        table = Table.objects.get(number=table_number)
    except Table.DoesNotExist:
        raise ValidationError("La mesa indicada no existe.", code="invalid")
    if table.status != Table.Status.FREE:
        raise ValidationError("La mesa no está libre.", code="not_free")

    order = Order.objects.create(table_number=table_number, waiter=waiter)
    table.status = Table.Status.OCCUPIED
    table.save(update_fields=["status"])
    return order


def is_pending_send(item):
    """RF-5: an addition the waiter hasn't sent yet. Private to the
    waiter: it never reaches the admin, the total, the charge, the stats
    or the kitchen until sent."""
    return item.line_type == OrderItem.LineType.ADDITION and item.sent_at is None


def exclude_pending_send(items):
    """Queryset form of `is_pending_send`: the lines that count."""
    return items.exclude(line_type=OrderItem.LineType.ADDITION, sent_at__isnull=True)


def pending_additions(order):
    return order.items.filter(
        line_type=OrderItem.LineType.ADDITION, sent_at__isnull=True
    )


def _discard_pending_additions(order):
    """An order that closes (charged or voided) drops the additions that
    were never sent — for the system they never existed (RF-5)."""
    pending_additions(order).delete()


def remove_item(order, item):
    """RF-2, RF-5: remove a line that never reached the system — any
    line of a draft, or an addition not sent yet. No reason, no trace."""
    item.refresh_from_db(fields=["sent_at"])
    if order.status != Order.Status.DRAFT and not (
        order.status == Order.Status.IN_PROGRESS and is_pending_send(item)
    ):
        raise ValidationError(
            "Solo se pueden quitar ítems de un pedido en borrador o "
            "adiciones sin enviar.",
            code="not_draft",
        )
    item.delete()


def delete_order(order):
    """RF-2: discard a draft order outright — no reason, no trace, same
    philosophy as remove_item. Never applies once the order was sent
    (use void_order, admin-only, after that point)."""
    if order.status != Order.Status.DRAFT:
        raise ValidationError(
            "Solo se puede eliminar un pedido en borrador.", code="not_draft"
        )
    _free_table(order.table_number)
    order.delete()


def register_action(
    order,
    action_type,
    performed_by,
    reason=None,
    item=None,
    from_table_number=None,
    to_table_number=None,
):
    """RF-12: write one traceability row for a sensitive order action."""
    return OrderAction.objects.create(
        order=order,
        action_type=action_type,
        performed_by=performed_by,
        reason=reason,
        item=item,
        from_table_number=from_table_number,
        to_table_number=to_table_number,
    )


def _free_table(table_number):
    if table_number is None:  # RF-18: a counter order holds no table.
        return
    Table.objects.filter(number=table_number).update(status=Table.Status.FREE)


def _validate_note(note):
    if note and len(note) > NOTE_MAX_LENGTH:
        raise ValidationError(
            f"La nota no puede superar los {NOTE_MAX_LENGTH} caracteres.",
            code="invalid",
        )


def _validate_off_menu_name(name):
    if not name or not name.strip():
        raise ValidationError(
            "El nombre del ítem no puede estar vacío.", code="invalid"
        )
    if len(name.strip()) > ITEM_NAME_MAX_LENGTH:
        raise ValidationError(
            f"El nombre no puede superar los {ITEM_NAME_MAX_LENGTH} caracteres.",
            code="invalid",
        )


def _validate_price(price):
    try:
        is_positive = price is not None and price > 0
    except TypeError:
        raise ValidationError(
            "El precio debe ser un valor numérico mayor que cero.", code="invalid"
        )
    if not is_positive:
        raise ValidationError(
            "El precio debe ser un valor numérico mayor que cero.", code="invalid"
        )


def add_item(
    order, product_id=None, name=None, price=None, quantity=1, note=""
):
    """RF-3, RF-4, RF-5: add a catalog or off-menu item to an order.

    `line_type` is inferred from the order's current status: `ORIGINAL`
    while still in "borrador" (draft), `ADDITION` once "en preparación".
    An addition starts unsent: nobody else sees it and nothing prints
    until the waiter sends it (send_additions) or prints (004 RF-1).

    A repeated item merges into the matching unsent line instead of
    adding a new one (see _find_mergeable_line).
    """
    if order.status in (Order.Status.CHARGED, Order.Status.VOIDED):
        raise ValidationError(
            "Este pedido no admite agregar ítems.", code="not_editable"
        )

    _validate_note(note)

    if product_id is not None:
        try:
            product = Product.objects.get(pk=product_id)
        except (Product.DoesNotExist, ValueError, TypeError):
            raise ValidationError("El producto no existe.", code="not_found")
        if not product.is_available:
            raise ValidationError(
                "El producto ya no está disponible.", code="not_available"
            )
        item_name = product.name
        item_price = product.price
        catalog_product = product
    else:
        _validate_off_menu_name(name)
        _validate_price(price)
        item_name = name.strip()
        item_price = price
        catalog_product = None

    line_type = (
        OrderItem.LineType.ORIGINAL
        if order.status == Order.Status.DRAFT
        else OrderItem.LineType.ADDITION
    )

    with transaction.atomic():
        existing = _find_mergeable_line(
            order, line_type, catalog_product, item_name, item_price
        )
        if existing is not None:
            return _merge_into_line(existing, quantity, note)
        return OrderItem.objects.create(
            order=order,
            catalog_product=catalog_product,
            name=item_name,
            unit_price=item_price,
            quantity=quantity,
            note=note or "",
            line_type=line_type,
        )


def _find_mergeable_line(order, line_type, catalog_product, name, unit_price):
    """RF-3: the unsent, active line a repeated item adds up to — same
    catalog product (or same off-menu name, ignoring case and extra
    spaces) at the same frozen price. A line already sent stays as it
    is: the repeat becomes its own line, so the kitchen ticket shows only
    what is new and voiding one never voids the others."""
    candidates = order.items.select_for_update().filter(
        line_type=line_type,
        is_voided=False,
        sent_at__isnull=True,
        unit_price=unit_price,
        catalog_product=catalog_product,
    ).order_by("id")
    if catalog_product is not None:
        return candidates.first()
    wanted = " ".join(name.split()).casefold()
    return next(
        (line for line in candidates if " ".join(line.name.split()).casefold() == wanted),
        None,
    )


def _merge_into_line(item, quantity, note):
    """RF-3, RF-4: add the quantity and put the new note on its own line
    under the existing ones, exactly as the waiter wrote it."""
    note = (note or "").strip()
    merged_note = item.note
    if note:
        merged_note = f"{item.note}\n{note}" if item.note else note
    if len(merged_note) > MERGED_NOTE_MAX_LENGTH:
        raise ValidationError(
            "La nota de este ítem ya es muy larga; agrégalo en una línea aparte.",
            code="invalid",
        )
    item.quantity += quantity
    item.note = merged_note
    item.save(update_fields=["quantity", "note"])
    return item


def send_additions(order, waiter):
    """RF-5: the waiter sends the additions still pending — from now on
    the admin sees them and they count in the total. Never prints: that
    is a separate, explicit action (004 RF-1)."""
    if order.waiter_id != waiter.id:
        raise ValidationError(
            "Solo el mesero dueño del pedido puede enviar adiciones.",
            code="not_owner",
        )
    if order.status != Order.Status.IN_PROGRESS:
        raise ValidationError(
            "Este pedido no admite enviar adiciones.", code="not_editable"
        )
    sent_count = pending_additions(order).update(sent_at=timezone.now())
    if not sent_count:
        raise ValidationError(
            "Este pedido no tiene adiciones sin enviar.", code="nothing_pending"
        )
    notify_orders_changed()
    return sent_count


def update_item_note(item, note):
    """RF-4: edit an existing item's note while it and its order are
    still active."""
    if item.is_voided or item.order.status in (
        Order.Status.CHARGED,
        Order.Status.VOIDED,
    ):
        raise ValidationError(
            "No se puede editar la nota de este ítem.", code="not_editable"
        )
    _validate_note(note)
    item.note = note
    item.save(update_fields=["note"])
    return item


def send_order(order):
    """RF-5: "Crear pedido" — draft -> in_progress. The admin sees it from
    now on, but nothing prints: the waiter prints when (and if) the
    kitchen needs it (004 RF-1). Resending an already-sent order is a
    silent no-op."""
    if order.status != Order.Status.DRAFT:
        return order
    if not order.items.filter(is_voided=False).exists():
        raise ValidationError("El pedido no tiene ningún ítem.", code="empty")

    with transaction.atomic():
        order.status = Order.Status.IN_PROGRESS
        _assign_daily_number(order)
        order.save(update_fields=["status", "daily_number", "sent_at"])
        order.items.update(sent_at=order.sent_at)
    notify_orders_changed()
    return order


def void_item(order, item, waiter, reason):
    """RF-6: void a single line of a sent order, with a reason.

    If this leaves the order with no active items, it auto-voids the
    whole order (RF-11), reusing this same waiter/reason instead of
    asking for a new one.
    """
    if order.status != Order.Status.IN_PROGRESS:
        raise ValidationError(
            "Este pedido no admite anulación de ítems.", code="not_editable"
        )
    # sent_at may have changed under this instance (send_additions
    # updates in bulk): decide from the stored value.
    item.refresh_from_db(fields=["sent_at"])
    if is_pending_send(item):
        raise ValidationError(
            "Esta adición todavía no se envió: elimínala en vez de anularla.",
            code="not_editable",
        )

    item.is_voided = True
    item.void_reason = reason
    item.save(update_fields=["is_voided", "void_reason"])
    register_action(
        order, OrderAction.ActionType.ITEM_VOIDED, waiter, reason=reason, item=item
    )

    # The void is on screen right away; its ticket waits for the next
    # "Imprimir pedido" (004 RF-1). An unsent addition still counts as
    # an active line here: the waiter is about to send it, so the order
    # is not auto-voided from under them.
    if not order.items.filter(is_voided=False).exists():
        order.status = Order.Status.VOIDED
        order.save(update_fields=["status"])
        _free_table(order.table_number)
        register_action(
            order, OrderAction.ActionType.ORDER_VOIDED_AUTO, waiter, reason=reason
        )

    notify_orders_changed()
    return item


def fix_table(order, waiter, new_table_number):
    """RF-7: correct an order's table to a free one; the owner never
    changes."""
    if order.status in (Order.Status.CHARGED, Order.Status.VOIDED):
        raise ValidationError(
            "Este pedido no admite corrección de mesa.", code="not_editable"
        )
    if order.table_number is None:
        raise ValidationError(
            "Un pedido de mostrador no tiene mesa que corregir.", code="not_editable"
        )
    try:
        destination = Table.objects.get(number=new_table_number)
    except Table.DoesNotExist:
        raise ValidationError("La mesa destino no existe.", code="invalid")
    if destination.status != Table.Status.FREE:
        raise ValidationError("La mesa destino no está libre.", code="not_free")

    original_table_number = order.table_number
    _free_table(original_table_number)
    destination.status = Table.Status.OCCUPIED
    destination.save(update_fields=["status"])
    order.table_number = new_table_number
    order.save(update_fields=["table_number"])
    register_action(
        order,
        OrderAction.ActionType.TABLE_CORRECTED,
        waiter,
        from_table_number=original_table_number,
        to_table_number=new_table_number,
    )
    return order


def set_admin_note(order, note):
    """RF-17: the admin's own note on an order, in any status. Never
    reaches waiters, the kitchen ticket or the customer receipt."""
    note = (note or "").strip()
    if len(note) > ADMIN_NOTE_MAX_LENGTH:
        raise ValidationError(
            f"La nota no puede superar los {ADMIN_NOTE_MAX_LENGTH} caracteres.",
            code="invalid",
        )
    order.admin_note = note
    order.save(update_fields=["admin_note"])
    notify_orders_changed()
    return order


def set_delivered(order, delivered):
    """RF-8: toggle the delivered flag, independent of the main status —
    except a voided order, where it stops being relevant."""
    if order.status == Order.Status.VOIDED:
        raise ValidationError(
            "Un pedido anulado no admite este cambio.", code="not_editable"
        )
    order.delivered = delivered
    order.save(update_fields=["delivered"])
    return order


def release_table(table_number):
    """RF-10: any waiter can free a paid table."""
    try:
        table = Table.objects.get(number=table_number)
    except Table.DoesNotExist:
        raise ValidationError("La mesa no existe.", code="invalid")
    if table.status != Table.Status.PAID:
        raise ValidationError("La mesa no está pagada.", code="not_paid")

    table.status = Table.Status.FREE
    table.save(update_fields=["status"])
    return table


def void_order(order, admin, reason):
    """RF-11: void a whole order (draft or in progress), with a reason.
    A charged order can never be voided (admin-only at the
    view/permission layer)."""
    if order.status == Order.Status.CHARGED:
        raise ValidationError(
            "Un pedido cobrado no puede anularse.", code="already_charged"
        )
    if order.status == Order.Status.VOIDED:
        raise ValidationError("Este pedido ya está anulado.", code="already_voided")

    order.status = Order.Status.VOIDED
    order.save(update_fields=["status"])
    _discard_pending_additions(order)
    _free_table(order.table_number)
    register_action(order, OrderAction.ActionType.ORDER_VOIDED, admin, reason=reason)
    notify_orders_changed()
    return order


def discard_draft_by_admin(order, admin):
    """RF-15: the admin frees a table held by a draft in one click. It is
    still a whole-order void (RF-11), traced with a fixed reason so the
    admin doesn't have to type one (constitution rule 4)."""
    if order.status != Order.Status.DRAFT:
        raise ValidationError(
            "Solo se puede eliminar un pedido en borrador.", code="not_draft"
        )
    return void_order(order, admin, DRAFT_DISCARD_REASON)
