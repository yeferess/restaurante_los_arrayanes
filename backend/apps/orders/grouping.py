"""RF-3: an order's active lines as people read them — every line of the
same product at the same price summed into one, with all their notes.

Display only: each line stays its own `OrderItem` underneath, so the
kitchen still gets "ADICION 1x" for a later addition (004) and a void
still targets exactly one line (RF-6).
"""

from dataclasses import dataclass, field
from decimal import Decimal


def normalize_name(name: str) -> str:
    """Off-menu names match ignoring case and extra spaces."""
    return " ".join(name.split()).casefold()


def same_item_key(item) -> tuple:
    """Two lines are "the same item" when they come from the same catalog
    product — or, off the menu, carry the same name — at the same frozen
    price."""
    if item.catalog_product_id is not None:
        return ("catalog", item.catalog_product_id, item.unit_price)
    return ("off_menu", normalize_name(item.name), item.unit_price)


@dataclass
class ItemGroup:
    name: str
    unit_price: Decimal
    parts: list = field(default_factory=list)

    @property
    def quantity(self) -> int:
        return sum(part.quantity for part in self.parts)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    @property
    def note(self) -> str:
        """Every part's note, one per line, in the order they were added."""
        return "\n".join(part.note for part in self.parts if part.note)


def group_items(items) -> list[ItemGroup]:
    """Active lines grouped by `same_item_key`, in the order each item
    first appeared. Voided lines are left out."""
    groups: dict[tuple, ItemGroup] = {}
    for item in sorted(items, key=lambda line: line.id):
        if item.is_voided:
            continue
        key = same_item_key(item)
        if key not in groups:
            groups[key] = ItemGroup(name=item.name, unit_price=item.unit_price)
        groups[key].parts.append(item)
    return list(groups.values())
