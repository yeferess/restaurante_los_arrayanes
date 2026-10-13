"use client";

import type { KeyboardEvent } from "react";
import { findMatch } from "@/lib/search";
import styles from "./MenuSearchBar.module.css";

/** The name with the part matching `query` wrapped in <mark> (ignoring
 * case and accents, 002 RF-9). */
export function HighlightedText({ text, query }: { text: string; query: string }) {
  const match = findMatch(text, query);
  if (!match) return <>{text}</>;
  return (
    <>
      {text.slice(0, match.start)}
      <mark className={styles.mark}>{text.slice(match.start, match.end)}</mark>
      {text.slice(match.end)}
    </>
  );
}

/** Search bar for the menu screens (002 RF-9): highlights instead of
 * hiding, shows "2 de 5" and jumps between matches with ▲ ▼ or Enter. */
export function MenuSearchBar({
  inputId,
  query,
  onQueryChange,
  count,
  index,
  onNext,
  onPrevious,
}: {
  inputId: string;
  query: string;
  onQueryChange: (value: string) => void;
  count: number;
  index: number;
  onNext: () => void;
  onPrevious: () => void;
}) {
  const searching = query.trim() !== "";

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (event.shiftKey) onPrevious();
    else onNext();
  }

  return (
    <div className={styles.bar} role="search">
      <label className={styles.label} htmlFor={inputId}>
        Buscar en el menú
      </label>
      <div className={styles.row}>
        <input
          id={inputId}
          className={styles.input}
          type="search"
          placeholder="Ej: bandeja"
          autoComplete="off"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className={styles.navButton}
          aria-label="Coincidencia anterior"
          onClick={onPrevious}
          disabled={count < 2}
        >
          ▲
        </button>
        <button
          type="button"
          className={styles.navButton}
          aria-label="Coincidencia siguiente"
          onClick={onNext}
          disabled={count < 2}
        >
          ▼
        </button>
      </div>
      {searching && (
        <p className={styles.status} role="status">
          {count === 0
            ? `No se encontró «${query.trim()}»`
            : `${index + 1} de ${count} ${count === 1 ? "coincidencia" : "coincidencias"}`}
        </p>
      )}
    </div>
  );
}
