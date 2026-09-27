"""Pure business logic for the menu module (RF-1..RF-6).

Kept free of HTTP/request concerns so it can be unit tested directly
(see specs/002-gestion-menu/plan.md, sections 1 and 6).
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError

from apps.menu.consumers import MENU_GROUP_NAME
from apps.menu.models import Category, Product

CATEGORY_NAME_MAX_LENGTH = 50
PRODUCT_NAME_MAX_LENGTH = 100


def _normalize(name):
    return name.strip().lower()


def notify_menu_changed():
    """RF-6: notify connected mesero apps that the menu changed.

    Call sites already match RF-6's scope decision: product writes
    always notify, category writes only via rename (see plan.md,
    section 4).
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        MENU_GROUP_NAME, {"type": "menu.actualizado"}
    )


def _validate_category_name(name):
    if not name or not name.strip():
        raise ValidationError(
            "El nombre de la categoría no puede estar vacío.", code="invalid"
        )
    if len(name.strip()) > CATEGORY_NAME_MAX_LENGTH:
        raise ValidationError(
            "El nombre de la categoría no puede superar los "
            f"{CATEGORY_NAME_MAX_LENGTH} caracteres.",
            code="invalid",
        )


def _ensure_category_name_is_unique(name, excluding=None):
    duplicates = Category.objects.filter(normalized_name=_normalize(name))
    if excluding is not None:
        duplicates = duplicates.exclude(pk=excluding.pk)
    if duplicates.exists():
        raise ValidationError(
            "Ya existe una categoría con ese nombre.", code="duplicate"
        )


def create_category(name):
    """RF-1: create a category."""
    _validate_category_name(name)
    _ensure_category_name_is_unique(name)
    return Category.objects.create(name=name.strip())


def rename_category(category, new_name):
    """RF-1: rename an existing category; propagates instantly via FK."""
    _validate_category_name(new_name)
    _ensure_category_name_is_unique(new_name, excluding=category)
    category.name = new_name.strip()
    category.save()
    notify_menu_changed()
    return category


def delete_category(category):
    """RF-1: refuse deletion while at least one product is assigned."""
    if category.products.exists():
        raise ValidationError(
            "Reasigna los productos de esta categoría antes de eliminarla.",
            code="has_products",
        )
    category.delete()


def _validate_product_name(name):
    if not name or not name.strip():
        raise ValidationError(
            "El nombre del producto no puede estar vacío.", code="invalid"
        )
    if len(name.strip()) > PRODUCT_NAME_MAX_LENGTH:
        raise ValidationError(
            "El nombre del producto no puede superar los "
            f"{PRODUCT_NAME_MAX_LENGTH} caracteres.",
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


def _get_existing_category(category_id):
    try:
        return Category.objects.get(pk=category_id)
    except (Category.DoesNotExist, ValueError, TypeError):
        raise ValidationError("La categoría indicada no existe.", code="invalid")


def _ensure_product_name_is_unique(name, excluding=None):
    duplicates = Product.objects.filter(normalized_name=_normalize(name))
    if excluding is not None:
        duplicates = duplicates.exclude(pk=excluding.pk)
    if duplicates.exists():
        raise ValidationError(
            "Ya existe un producto con ese nombre.", code="duplicate"
        )


def create_product(name, category_id, price, is_available=None):
    """RF-2: create a product; `category_id` must reference an existing
    category, selected from a list (never free text)."""
    if not Category.objects.exists():
        raise ValidationError(
            "Debes crear al menos una categoría antes de crear un producto.",
            code="no_categories",
        )
    _validate_product_name(name)
    _validate_price(price)
    _ensure_product_name_is_unique(name)
    category = _get_existing_category(category_id)
    product = Product.objects.create(
        name=name.strip(),
        category=category,
        price=price,
        is_available=True if is_available is None else is_available,
    )
    notify_menu_changed()
    return product


def update_product(product, name=None, category_id=None, price=None):
    """RF-3: edit name/category/price; unspecified fields are left as-is."""
    if name is not None:
        _ensure_product_name_is_unique(name, excluding=product)
        product.name = name.strip()
    if category_id is not None:
        product.category = _get_existing_category(category_id)
    if price is not None:
        _validate_price(price)
        product.price = price
    product.save()
    notify_menu_changed()
    return product


def set_product_availability(product, is_available):
    """RF-4: toggle availability without touching any other field."""
    product.is_available = is_available
    product.save(update_fields=["is_available"])
    notify_menu_changed()
    return product


def delete_product(product):
    """RF-5: permanent deletion, regardless of order history — order
    lines keep their own copy of name/price, so nothing references this
    row (see plan.md, section 2)."""
    product.delete()
    notify_menu_changed()
