import { describe, it, expect } from "vitest";
import {
  computeSystemHealth,
  ROYALTY_CRASH_THRESHOLD,
  QUOTA_HIGH_THRESHOLD,
  ROI_THRESHOLD_PCT,
} from "@/lib/health-engine";
import type { HealthSnapshot } from "@/lib/health-engine";

/** Nominal snapshot where everything is fine -> GREEN */
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

describe("health-engine: boundary tests", () => {
  it("royaltyDropPercent exactly at ROYALTY_CRASH_THRESHOLD -> RED", () => {
    const snap = nominalSnapshot();
    snap.royaltyDropPercent = ROYALTY_CRASH_THRESHOLD;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
  });

  it("royaltyDropPercent = ROYALTY_CRASH_THRESHOLD + 0.001 -> NOT RED", () => {
    const snap = nominalSnapshot();
    snap.royaltyDropPercent = ROYALTY_CRASH_THRESHOLD + 0.001;
    const result = computeSystemHealth(snap);
    expect(result.state).not.toBe("RED");
  });

  it("royaltyDropPercent = ROYALTY_CRASH_THRESHOLD - 1 -> RED (worse)", () => {
    const snap = nominalSnapshot();
    snap.royaltyDropPercent = ROYALTY_CRASH_THRESHOLD - 1;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("RED");
  });

  it("quotaUsedPercent exactly at QUOTA_HIGH_THRESHOLD -> ORANGE", () => {
    const snap = nominalSnapshot();
    snap.quotaUsedPercent = QUOTA_HIGH_THRESHOLD;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("ORANGE");
  });

  it("quotaUsedPercent = QUOTA_HIGH_THRESHOLD - 1 -> NOT ORANGE for quota alone", () => {
    const snap = nominalSnapshot();
    snap.quotaUsedPercent = QUOTA_HIGH_THRESHOLD - 1;
    const result = computeSystemHealth(snap);
    expect(result.state).not.toBe("ORANGE");
  });

  it("roiPercent exactly at ROI_THRESHOLD_PCT -> NOT YELLOW", () => {
    const snap = nominalSnapshot();
    snap.roiPercent = ROI_THRESHOLD_PCT;
    const result = computeSystemHealth(snap);
    expect(result.state).not.toBe("YELLOW");
  });

  it("roiPercent = ROI_THRESHOLD_PCT - 0.001 -> YELLOW", () => {
    const snap = nominalSnapshot();
    snap.roiPercent = ROI_THRESHOLD_PCT - 0.001;
    const result = computeSystemHealth(snap);
    expect(result.state).toBe("YELLOW");
  });

  it("unackedAlertCount does not affect state (1000 unacked, no P0)", () => {
    const snap = nominalSnapshot();
    snap.unackedAlertCount = 1000;
    const result = computeSystemHealth(snap);
    // Should still be GREEN since unackedAlertCount is not a trigger
    expect(result.state).toBe("GREEN");
  });
});

describe("health-engine: message precision tests", () => {
  it("royaltyDropPercent = -30.0 -> message contains '30%' (not '-30%')", () => {
    const snap = nominalSnapshot();
    snap.royaltyDropPercent = -30.0;
    const result = computeSystemHealth(snap);
    expect(result.humanMessage).toContain("30%");
    expect(result.humanMessage).not.toContain("-30%");
  });

  it("royaltyDropPercent = -30.7 -> message contains '31%' (rounded)", () => {
    const snap = nominalSnapshot();
    snap.royaltyDropPercent = -30.7;
    const result = computeSystemHealth(snap);
    // Math.abs(-30.7).toFixed(0) = "31"
    expect(result.humanMessage).toContain("31%");
  });

  it("roiPercent = 14.0 -> message contains '14.0%'", () => {
    const snap = nominalSnapshot();
    snap.roiPercent = 14.0;
    const result = computeSystemHealth(snap);
    expect(result.humanMessage).toContain("14.0%");
  });

  it("roiPercent = 14.567 -> message contains '14.6%' (1 decimal)", () => {
    const snap = nominalSnapshot();
    snap.roiPercent = 14.567;
    const result = computeSystemHealth(snap);
    // (14.567).toFixed(1) = "14.6"
    expect(result.humanMessage).toContain("14.6%");
  });
});

describe("health-engine: details field immutability", () => {
  it("mutating returned details does not affect subsequent calls", () => {
    const snap = nominalSnapshot();
    const result1 = computeSystemHealth(snap);
    // Mutate the returned details
    result1.details.killswitch = true;
    result1.details.criticalAlerts = 999;

    const result2 = computeSystemHealth(snap);
    // Second call should reflect the original snapshot, not the mutation
    expect(result2.details.killswitch).toBe(false);
    expect(result2.details.criticalAlerts).toBe(0);
  });

  it("details.killswitch matches snapshot.killswitchActive in all states", () => {
    // GREEN state
    const snapGreen = nominalSnapshot();
    expect(computeSystemHealth(snapGreen).details.killswitch).toBe(false);

    // BLACK state
    const snapBlack = nominalSnapshot();
    snapBlack.killswitchActive = true;
    expect(computeSystemHealth(snapBlack).details.killswitch).toBe(true);

    // RED state
    const snapRed = nominalSnapshot();
    snapRed.p0AlertCount = 1;
    expect(computeSystemHealth(snapRed).details.killswitch).toBe(false);

    // ORANGE state
    const snapOrange = nominalSnapshot();
    snapOrange.pendingPoliciesCount = 1;
    expect(computeSystemHealth(snapOrange).details.killswitch).toBe(false);

    // YELLOW state
    const snapYellow = nominalSnapshot();
    snapYellow.roiPercent = ROI_THRESHOLD_PCT - 1;
    expect(computeSystemHealth(snapYellow).details.killswitch).toBe(false);
  });
});
