import { describe, it, expect, beforeEach } from "vitest";
import {
  computeSystemHealth,
  ROI_THRESHOLD_PCT,
  ROYALTY_CRASH_THRESHOLD,
  QUOTA_HIGH_THRESHOLD,
} from "@/lib/health-engine";
import type { HealthSnapshot } from "@/lib/health-engine";

/** Nominal snapshot where everything is fine → GREEN */
function nominalSnapshot(): HealthSnapshot {
  return {
    killswitchActive: false,
    p0AlertCount: 0,
    royaltyDropPercent: 0,
    pendingPoliciesCount: 0,
    quotaUsedPercent: 0,
    roiPercent: ROI_THRESHOLD_PCT + 5,
    unackedAlertCount: 0,
  };
}

describe("health-engine: BLACK state", () => {
  let snap: HealthSnapshot;
  beforeEach(() => {
    snap = nominalSnapshot();
  });

  it("returns BLACK when killswitch is active", () => {
    snap.killswitchActive = true;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("BLACK");
    expect(result.humanMessage).toBe(
      "Killswitch active — all operations halted",
    );
  });

  it("BLACK overrides all other bad values", () => {
    snap.killswitchActive = true;
    snap.p0AlertCount = 5;
    snap.royaltyDropPercent = -50;
    snap.pendingPoliciesCount = 3;
    snap.quotaUsedPercent = 95;
    snap.roiPercent = 0;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("BLACK");
  });

  it("killswitch active + P0 alerts -> still BLACK", () => {
    snap.killswitchActive = true;
    snap.p0AlertCount = 2;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("BLACK");
  });

  it("killswitch false does not produce BLACK", () => {
    snap.killswitchActive = false;
    const result = computeSystemHealth(snap);
    expect(result.state).not.toBe("BLACK");
  });
});

describe("health-engine: RED state", () => {
  let snap: HealthSnapshot;
  beforeEach(() => {
    snap = nominalSnapshot();
  });

  it("P0 count = 1 -> RED with singular alert", () => {
    snap.p0AlertCount = 1;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
    expect(result.humanMessage).toBe("CRITICAL: 1 P0 alert");
  });

  it("P0 count = 3 -> RED with plural alerts", () => {
    snap.p0AlertCount = 3;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
    expect(result.humanMessage).toBe("CRITICAL: 3 P0 alerts");
  });

  it("royaltyDropPercent = -31 -> RED (below threshold)", () => {
    snap.royaltyDropPercent = -31;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
    expect(result.humanMessage).toContain("31%");
  });

  it("royaltyDropPercent = -30 -> RED (at threshold, equal is RED)", () => {
    snap.royaltyDropPercent = -30;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
    expect(result.humanMessage).toContain("30%");
  });

  it("royaltyDropPercent = -29 -> NOT RED", () => {
    snap.royaltyDropPercent = -29;
    const result = computeSystemHealth(snap);
    expect(result.state).not.toBe("RED");
  });

  it("both P0 + royalty crash -> RED with combined message", () => {
    snap.p0AlertCount = 2;
    snap.royaltyDropPercent = -40;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
    expect(result.humanMessage).toBe(
      "CRITICAL: 2 P0 alerts + royalty crashed 40%",
    );
  });

  it("P0 only -> message without royalty", () => {
    snap.p0AlertCount = 1;
    snap.royaltyDropPercent = 0;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
    expect(result.humanMessage).not.toContain("royalty");
  });

  it("royalty crash only -> message without P0", () => {
    snap.royaltyDropPercent = -35;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
    expect(result.humanMessage).toBe(
      "Royalty crashed 35% vs prior period",
    );
    expect(result.humanMessage).not.toContain("P0");
  });
});

describe("health-engine: ORANGE state", () => {
  let snap: HealthSnapshot;
  beforeEach(() => {
    snap = nominalSnapshot();
  });

  it("pendingPolicies = 1 -> ORANGE with singular policy", () => {
    snap.pendingPoliciesCount = 1;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
    expect(result.humanMessage).toBe("1 policy pending approval");
  });

  it("pendingPolicies = 3 -> ORANGE with plural policies", () => {
    snap.pendingPoliciesCount = 3;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
    expect(result.humanMessage).toBe("3 policies pending approval");
  });

  it("quota = 80 -> ORANGE (at threshold)", () => {
    snap.quotaUsedPercent = 80;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
    expect(result.humanMessage).toContain("80%");
  });

  it("quota = 79 -> NOT ORANGE for quota alone", () => {
    snap.quotaUsedPercent = 79;
    const result = computeSystemHealth(snap);
    expect(result.state).not.toBe("ORANGE");
  });

  it("both policies + quota -> ORANGE with combined message", () => {
    snap.pendingPoliciesCount = 2;
    snap.quotaUsedPercent = 90;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
    expect(result.humanMessage).toBe(
      "2 policies pending approval · quota at 90%",
    );
  });

  it("policies only -> no quota in message", () => {
    snap.pendingPoliciesCount = 1;
    snap.quotaUsedPercent = 50;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
    expect(result.humanMessage).not.toContain("quota");
  });

  it("quota only -> no policies in message", () => {
    snap.quotaUsedPercent = 85;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
    expect(result.humanMessage).not.toContain("polic");
  });
});

describe("health-engine: YELLOW state", () => {
  let snap: HealthSnapshot;
  beforeEach(() => {
    snap = nominalSnapshot();
  });

  it("roi just below threshold -> YELLOW", () => {
    snap.roiPercent = ROI_THRESHOLD_PCT - 0.1;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("YELLOW");
    expect(result.humanMessage).toContain(
      `${(ROI_THRESHOLD_PCT - 0.1).toFixed(1)}%`,
    );
  });

  it("roi = ROI_THRESHOLD_PCT -> NOT YELLOW (at threshold = ok)", () => {
    snap.roiPercent = ROI_THRESHOLD_PCT;
    const result = computeSystemHealth(snap);
    expect(result.state).not.toBe("YELLOW");
  });

  it("roi = 0 -> YELLOW with 0.0% in message", () => {
    snap.roiPercent = 0;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("YELLOW");
    expect(result.humanMessage).toContain("0.0%");
  });
});

describe("health-engine: GREEN state", () => {
  let snap: HealthSnapshot;
  beforeEach(() => {
    snap = nominalSnapshot();
  });

  it("all nominal -> GREEN", () => {
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("GREEN");
    expect(result.humanMessage).toBe("All systems nominal");
  });

  it("edge: p0=0, drop=0, policies=0, quota=0, roi=ROI_THRESHOLD_PCT -> GREEN", () => {
    snap.p0AlertCount = 0;
    snap.royaltyDropPercent = 0;
    snap.pendingPoliciesCount = 0;
    snap.quotaUsedPercent = 0;
    snap.roiPercent = ROI_THRESHOLD_PCT;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("GREEN");
  });
});

describe("health-engine: priority tests", () => {
  let snap: HealthSnapshot;
  beforeEach(() => {
    snap = nominalSnapshot();
  });

  it("RED beats ORANGE (P0 alert + pending policies)", () => {
    snap.p0AlertCount = 1;
    snap.pendingPoliciesCount = 2;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
  });

  it("RED beats YELLOW (P0 alert + low ROI)", () => {
    snap.p0AlertCount = 1;
    snap.roiPercent = 5;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
  });

  it("ORANGE beats YELLOW (pending policies + low ROI)", () => {
    snap.pendingPoliciesCount = 1;
    snap.roiPercent = 5;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
  });

  it("BLACK beats RED (killswitch + P0)", () => {
    snap.killswitchActive = true;
    snap.p0AlertCount = 3;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("BLACK");
  });
});

describe("health-engine: details field", () => {
  it("always populated correctly regardless of state", () => {
    const snap: HealthSnapshot = {
      killswitchActive: false,
      p0AlertCount: 2,
      royaltyDropPercent: -15,
      pendingPoliciesCount: 3,
      quotaUsedPercent: 75,
      roiPercent: 12,
      unackedAlertCount: 5,
    };
    const result = computeSystemHealth(snap);
    expect(result.details).toEqual({
      killswitch: false,
      criticalAlerts: 2,
      royaltyDrop: -15,
      pendingPolicies: 3,
      quotaUsed: 75,
      roi: 12,
    });
  });

  it("reflects raw snapshot values even when GREEN", () => {
    const snap = nominalSnapshot();
    snap.roiPercent = 25;
    snap.quotaUsedPercent = 50;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("GREEN");
    expect(result.details.roi).toBe(25);
    expect(result.details.quotaUsed).toBe(50);
  });
});

describe("health-engine: message format", () => {
  it("royalty crash message includes absolute value (no minus sign)", () => {
    const snap = nominalSnapshot();
    snap.royaltyDropPercent = -42;
    const result = computeSystemHealth(snap);
    expect(result.humanMessage).toContain("42%");
    expect(result.humanMessage).not.toContain("-42%");
  });

  it("royalty drop exactly -30 -> '30%' in message (not '-30%')", () => {
    const snap = nominalSnapshot();
    snap.royaltyDropPercent = -30;
    const result = computeSystemHealth(snap);
    expect(result.humanMessage).toContain("30%");
    expect(result.humanMessage).not.toContain("-30%");
  });
});
