"use client";

import { useEffect, useState } from "react";
import { matchesSearch } from "@/lib/search";

/** 002 RF-9: search over a menu list without hiding anything — which
 * items match, which one is the current one, and moving between them.
 * The current match is scrolled into view; its element must have the id
 * `${idPrefix}-${item.id}`. */
export function useMenuSearch<T extends { id: number; name: string }>(
  items: T[],
  idPrefix: string
) {
  const [query, setQueryState] = useState("");
  const [position, setPosition] = useState(0);

  const matchIds = query.trim()
    ? items.filter((item) => matchesSearch(item.name, query)).map((item) => item.id)
    : [];
  const count = matchIds.length;
  const index = count === 0 ? -1 : Math.min(position, count - 1);
  const activeId = index === -1 ? null : matchIds[index];

  useEffect(() => {
    if (activeId === null) return;
    const element = document.getElementById(`${idPrefix}-${activeId}`);
    element?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  }, [activeId, idPrefix, query]);

  function setQuery(value: string) {
    setQueryState(value);
    setPosition(0);
  }

  function next() {
    if (count > 0) setPosition((index + 1) % count);
  }

  function previous() {
    if (count > 0) setPosition((index - 1 + count) % count);
  }

  return {
    query,
    setQuery,
    count,
    index,
    activeId,
    isMatch: (id: number) => matchIds.includes(id),
    next,
    previous,
  };
}
