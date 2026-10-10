import { describe, it, expect } from "vitest";
import { formatPrice } from "./format";

describe("formatPrice", () => {
  it("adds a thousands separator", () => {
    expect(formatPrice("20000.00")).toBe("20.000,00");
  });

  it("uses a comma as the decimal separator", () => {
    expect(formatPrice("4.50")).toBe("4,50");
  });

  it("accepts a plain number, not only a string", () => {
    expect(formatPrice(9)).toBe("9,00");
  });

  it("always shows exactly two decimals", () => {
    expect(formatPrice("32.5")).toBe("32,50");
  });
});
