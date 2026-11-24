import { describe, expect, it } from "vitest";
import {
  delayTone,
  evidenceLabel,
  formatMinutes,
  humanise,
  numberOrDash,
  severityClass,
  statusClass,
  titleCase,
} from "./format";

describe("formatMinutes", () => {
  it("formats minutes past midnight as a zero-padded clock", () => {
    expect(formatMinutes(0)).toBe("00:00");
    expect(formatMinutes(65)).toBe("01:05");
    expect(formatMinutes(23 * 60 + 59)).toBe("23:59");
  });

  it("wraps values past a day and handles missing values", () => {
    expect(formatMinutes(1440 + 90)).toBe("01:30");
    expect(formatMinutes(-15)).toBe("23:45");
    expect(formatMinutes(null)).toBe("—");
    expect(formatMinutes(undefined)).toBe("—");
  });
});

describe("badge helpers", () => {
  it("maps severity and status to css class names", () => {
    expect(severityClass("CRITICAL")).toBe("severity severity-critical");
    expect(statusClass("AT_STATION")).toBe("status status-at-station");
  });

  it("gives honest evidence labels", () => {
    expect(evidenceLabel("VALIDATED")).toMatch(/independently validated/i);
    expect(evidenceLabel("MODEL_DISAGREEMENT")).toMatch(/human review/i);
    expect(evidenceLabel("NO_FEASIBLE_SOLUTION")).toBe("No feasible solution");
  });
});

describe("number helpers", () => {
  it("renders a dash for absent numbers instead of inventing zero", () => {
    expect(numberOrDash(null)).toBe("—");
    expect(numberOrDash(undefined)).toBe("—");
    expect(numberOrDash(Number.NaN)).toBe("—");
    expect(numberOrDash(1.234, 2)).toBe("1.23");
  });

  it("tone thresholds are monotonic", () => {
    expect(delayTone(0)).toBe("delay-good");
    expect(delayTone(10)).toBe("delay-watch");
    expect(delayTone(40)).toBe("delay-bad");
  });
});

describe("text helpers", () => {
  it("humanises snake case and title cases labels", () => {
    expect(humanise("USER_LOGIN")).toBe("User Login");
    expect(titleCase("BLOCK_CLOSURE")).toBe("Block Closure");
  });
});
