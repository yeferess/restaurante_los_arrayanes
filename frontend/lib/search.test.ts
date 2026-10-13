import { describe, it, expect } from "vitest";
import { findMatch, matchesSearch, normalizeSearch } from "./search";

describe("lib/search (003 RF-3, 002 RF-9)", () => {
  it("ignores case and accents", () => {
    expect(normalizeSearch("Canción")).toBe("cancion");
    expect(matchesSearch("Canción", "cancion")).toBe(true);
    expect(matchesSearch("canción", "CANCIÓN")).toBe(true);
    expect(matchesSearch("Café", "CAFE")).toBe(true);
  });

  it("treats ñ as n", () => {
    expect(matchesSearch("Jugo de piña", "pina")).toBe(true);
  });

  it("matches anywhere in the name", () => {
    expect(matchesSearch("Jugo de mora", "mora")).toBe(true);
    expect(matchesSearch("Jugo de mora", "fresa")).toBe(false);
  });

  it("an empty or blank query matches nothing", () => {
    expect(findMatch("Bandeja paisa", "")).toBeNull();
    expect(findMatch("Bandeja paisa", "   ")).toBeNull();
  });

  it("returns the position in the original text, accents included", () => {
    expect(findMatch("Canción del día", "cancion")).toEqual({ start: 0, end: 7 });
    expect(findMatch("Jugo de mora", "MORA")).toEqual({ start: 8, end: 12 });
    expect(findMatch("Ají casero", "aji")).toEqual({ start: 0, end: 3 });
  });

  it("keeps a decomposed accent inside the highlighted part", () => {
    const decomposed = "Café negro"; // "Café" written as e + combining accent
    expect(findMatch(decomposed, "cafe")).toEqual({ start: 0, end: 5 });
  });
});
