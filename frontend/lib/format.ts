/** Formats a price (backend decimal string or number) with Colombian
 * thousands/decimal separators (ej. 20000 -> "20.000,00") — display
 * only, never used for calculations. */
export function formatPrice(value: string | number): string {
  const numeric = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("es-CO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric);
}
