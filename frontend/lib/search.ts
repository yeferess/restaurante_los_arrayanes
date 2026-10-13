// Menu search helpers (003 RF-3, 002 RF-9). Display-only: they filter or
// highlight the menu already loaded from the backend, which still
// validates every product added to an order.

const DIACRITICS = /\p{Diacritic}/gu;

/** Lowercase and without accents: "Canción", "CANCION" and "cancion"
 * all become "cancion" (and "Piña" becomes "pina"). */
export function normalizeSearch(text: string): string {
  return text.normalize("NFD").replace(DIACRITICS, "").toLowerCase();
}

export type SearchMatch = { start: number; end: number };

/** Where `query` appears inside `text`, ignoring case and accents, as
 * [start, end) indexes of the ORIGINAL text so it can be highlighted
 * with its accents. `null` when there is no match or the query is empty. */
export function findMatch(text: string, query: string): SearchMatch | null {
  const needle = normalizeSearch(query).trim();
  if (!needle) return null;

  // Normalize char by char, remembering which original char each
  // normalized char came from.
  let normalized = "";
  const origin: number[] = [];
  for (let i = 0; i < text.length; i++) {
    const piece = normalizeSearch(text[i]);
    for (const char of piece) {
      normalized += char;
      origin.push(i);
    }
  }

  const index = normalized.indexOf(needle);
  if (index === -1) return null;
  let end = origin[index + needle.length - 1] + 1;
  // Keep any combining accent right after the match inside it.
  while (end < text.length && normalizeSearch(text[end]) === "") end++;
  return { start: origin[index], end };
}

export function matchesSearch(text: string, query: string): boolean {
  return findMatch(text, query) !== null;
}
