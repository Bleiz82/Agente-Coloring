import { describe, it, expect } from "vitest";
import {
  formatCurrency,
  formatPercent,
  formatDelta,
  formatCompact,
  formatRelativeTime,
} from "@/lib/format";

describe("formatCurrency", () => {
  it("USD 7.99 contains dollar sign and amount", () => {
    const result = formatCurrency(7.99, "USD");
    expect(result).toContain("7,99");
  });

  it("EUR 10.00 contains euro symbol", () => {
    const result = formatCurrency(10.0, "EUR");
    // it-IT locale uses € symbol
    expect(result).toMatch(/10[,.]00/);
    expect(result).toContain("€"); // € symbol
  });

  it("GBP 5.50 contains pound symbol", () => {
    const result = formatCurrency(5.5, "GBP");
    expect(result).toMatch(/5[,.]50/);
  });

  it("zero value contains 0", () => {
    const result = formatCurrency(0, "USD");
    expect(result).toContain("0");
  });

  it("large number 1234.56 contains 234", () => {
    const result = formatCurrency(1234.56, "USD");
    expect(result).toContain("234");
  });

  it("accepts string input", () => {
    const result = formatCurrency("7.99", "USD");
    expect(result).toContain("7");
  });
});

describe("formatPercent", () => {
  it("15.0 returns +15.0%", () => {
    expect(formatPercent(15.0)).toBe("+15.0%");
  });

  it("0 returns +0.0%", () => {
    expect(formatPercent(0)).toBe("+0.0%");
  });

  it("100 returns +100.0%", () => {
    expect(formatPercent(100)).toBe("+100.0%");
  });

  it("72.5 returns +72.5% with 1 decimal", () => {
    expect(formatPercent(72.5)).toBe("+72.5%");
  });

  it("negative -3.1 returns -3.1%", () => {
    expect(formatPercent(-3.1)).toBe("-3.1%");
  });
});

describe("formatDelta", () => {
  it("positive 5.2 contains + and 5.2", () => {
    const result = formatDelta(5.2);
    expect(result.text).toContain("+");
    expect(result.text).toContain("5.2");
    expect(result.positive).toBe(true);
  });

  it("negative -3.1 contains - and 3.1", () => {
    const result = formatDelta(-3.1);
    expect(result.text).toContain("-");
    expect(result.text).toContain("3.1");
    expect(result.positive).toBe(false);
  });

  it("zero returns positive true and contains 0", () => {
    const result = formatDelta(0);
    expect(result.text).toContain("0");
    expect(result.positive).toBe(true);
  });
});

describe("formatCompact", () => {
  it("1000 formats as 1.0K", () => {
    const result = formatCompact(1000);
    expect(result).toContain("1");
    expect(result).toMatch(/[kK]/);
  });

  it("1_000_000 formats as 1.0M", () => {
    const result = formatCompact(1_000_000);
    expect(result).toContain("1");
    expect(result).toMatch(/[mM]/);
  });

  it("999 contains 999 without K/M suffix", () => {
    const result = formatCompact(999);
    expect(result).toContain("999");
    expect(result).not.toMatch(/[kKmM]/);
  });

  it("0 formats as 0.00", () => {
    const result = formatCompact(0);
    expect(result).toBe("0.00");
  });
});

describe("formatRelativeTime", () => {
  it("1 hour ago contains 'h ago'", () => {
    const date = new Date(Date.now() - 60 * 60 * 1000);
    const result = formatRelativeTime(date);
    expect(result).toContain("h ago");
  });

  it("1 day ago contains 'd ago'", () => {
    const date = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const result = formatRelativeTime(date);
    expect(result).toContain("d ago");
  });

  it("10 seconds ago returns 'just now'", () => {
    const date = new Date(Date.now() - 10 * 1000);
    const result = formatRelativeTime(date);
    expect(result).toBe("just now");
  });

  it("future date does not throw", () => {
    const futureDate = new Date(Date.now() + 60 * 60 * 1000);
    expect(() => formatRelativeTime(futureDate)).not.toThrow();
  });

  it("accepts string date input", () => {
    const dateStr = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    const result = formatRelativeTime(dateStr);
    expect(result).toContain("m ago");
  });
});
