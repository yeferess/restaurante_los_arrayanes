import type { ItemGroup, OrderItem } from "./orders";

/** Test-only: the `item_groups` the backend would send for lines that
 * are all different items — one group per active line. */
export function oneGroupPerItem(items: OrderItem[]): ItemGroup[] {
  return items
    .filter((item) => !item.is_voided)
    .map((item) => ({
      name: item.name,
      unit_price: item.unit_price,
      quantity: item.quantity,
      line_total: item.line_total,
      note: item.note,
      parts: [
        {
          item_id: item.id,
          quantity: item.quantity,
          line_type: item.line_type,
          pending_send: item.pending_send ?? false,
          note: item.note,
        },
      ],
    }));
}
