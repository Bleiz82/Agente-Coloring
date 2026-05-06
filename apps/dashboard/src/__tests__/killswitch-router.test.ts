import { describe, it, expect } from "vitest";

/**
 * Unit tests for killswitch activation logic.
 *
 * The killswitch state is stored in the database as a SystemState row
 * with key = "KILLSWITCH" and value = "ACTIVE" | "INACTIVE".
 *
 * These tests validate the boolean derivation logic without requiring
 * a real DB or tRPC context.
 */

/** Derives killswitch active boolean from a SystemState row value */
function isKillswitchActive(value: string | null | undefined): boolean {
  return value === "ACTIVE";
}

describe("killswitch: state parsing logic", () => {
  it('value "ACTIVE" -> killswitch is active', () => {
    expect(isKillswitchActive("ACTIVE")).toBe(true);
  });

  it('value "INACTIVE" -> killswitch is not active', () => {
    expect(isKillswitchActive("INACTIVE")).toBe(false);
  });

  it("value null (no row) -> killswitch is not active", () => {
    expect(isKillswitchActive(null)).toBe(false);
  });

  it("value undefined (missing field) -> killswitch is not active", () => {
    expect(isKillswitchActive(undefined)).toBe(false);
  });

  it('arbitrary string value "PAUSED" -> killswitch is not active', () => {
    expect(isKillswitchActive("PAUSED")).toBe(false);
  });
});

describe("killswitch: SystemState row derivation", () => {
  it("row with value ACTIVE -> row.value === ACTIVE is true", () => {
    const row = { key: "KILLSWITCH", value: "ACTIVE" };
    expect(row.value === "ACTIVE").toBe(true);
  });

  it("row with value INACTIVE -> row.value === ACTIVE is false", () => {
    const row = { key: "KILLSWITCH", value: "INACTIVE" };
    expect(row.value === "ACTIVE").toBe(false);
  });

  it("null row -> safe access returns false", () => {
    // Simulate a DB query returning null (no row found)
    const row = null as { key: string; value: string } | null;
    const value = row?.value ?? null;
    expect(isKillswitchActive(value)).toBe(false);
  });
});
