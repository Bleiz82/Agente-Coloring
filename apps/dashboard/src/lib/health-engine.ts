// ColorForge AI — System Health Engine
// Pure TypeScript module, no side-effects, no framework imports.

export type BeaconState = "GREEN" | "YELLOW" | "ORANGE" | "RED" | "BLACK";

export interface HealthSnapshot {
  killswitchActive: boolean;
  p0AlertCount: number;
  royaltyDropPercent: number;
  pendingPoliciesCount: number;
  quotaUsedPercent: number;
  roiPercent: number;
  unackedAlertCount: number;
}

export interface HealthResult {
  state: BeaconState;
  humanMessage: string;
  details: {
    killswitch: boolean;
    criticalAlerts: number;
    royaltyDrop: number;
    pendingPolicies: number;
    quotaUsed: number;
    roi: number;
  };
}

// Thresholds (exported so tests can reference them)
export const ROI_THRESHOLD_PCT = 15;
export const ROYALTY_CRASH_THRESHOLD = -30;
export const QUOTA_HIGH_THRESHOLD = 80;

export function computeSystemHealth(snapshot: HealthSnapshot): HealthResult {
  const details = {
    killswitch: snapshot.killswitchActive,
    criticalAlerts: snapshot.p0AlertCount,
    royaltyDrop: snapshot.royaltyDropPercent,
    pendingPolicies: snapshot.pendingPoliciesCount,
    quotaUsed: snapshot.quotaUsedPercent,
    roi: snapshot.roiPercent,
  };

  // 1. BLACK: killswitch active
  if (snapshot.killswitchActive) {
    return {
      state: "BLACK",
      humanMessage: "Killswitch active — all operations halted",
      details,
    };
  }

  // 2. RED: P0 alerts or royalty crash
  const hasP0 = snapshot.p0AlertCount > 0;
  const hasRoyaltyCrash =
    snapshot.royaltyDropPercent <= ROYALTY_CRASH_THRESHOLD;

  if (hasP0 || hasRoyaltyCrash) {
    let humanMessage: string;
    const p0Plural = snapshot.p0AlertCount > 1 ? "s" : "";
    const absRoyalty = Math.abs(snapshot.royaltyDropPercent).toFixed(0);

    if (hasP0 && hasRoyaltyCrash) {
      humanMessage = `CRITICAL: ${snapshot.p0AlertCount} P0 alert${p0Plural} + royalty crashed ${absRoyalty}%`;
    } else if (hasP0) {
      humanMessage = `CRITICAL: ${snapshot.p0AlertCount} P0 alert${p0Plural}`;
    } else {
      humanMessage = `Royalty crashed ${absRoyalty}% vs prior period`;
    }

    return { state: "RED", humanMessage, details };
  }

  // 3. ORANGE: pending policies or quota high
  const hasPolicies = snapshot.pendingPoliciesCount > 0;
  const hasHighQuota = snapshot.quotaUsedPercent >= QUOTA_HIGH_THRESHOLD;

  if (hasPolicies || hasHighQuota) {
    let humanMessage: string;
    const policyPlural =
      snapshot.pendingPoliciesCount > 1 ? "ies" : "y";

    if (hasPolicies && hasHighQuota) {
      humanMessage = `${snapshot.pendingPoliciesCount} polic${policyPlural} pending approval · quota at ${snapshot.quotaUsedPercent}%`;
    } else if (hasPolicies) {
      humanMessage = `${snapshot.pendingPoliciesCount} polic${policyPlural} pending approval`;
    } else {
      humanMessage = `Quota at ${snapshot.quotaUsedPercent}% — approaching limit`;
    }

    return { state: "ORANGE", humanMessage, details };
  }

  // 4. YELLOW: ROI below target
  if (snapshot.roiPercent < ROI_THRESHOLD_PCT) {
    return {
      state: "YELLOW",
      humanMessage: `ROI at ${snapshot.roiPercent.toFixed(1)}% — below ${ROI_THRESHOLD_PCT}% target`,
      details,
    };
  }

  // 5. GREEN: all clear
  return {
    state: "GREEN",
    humanMessage: "All systems nominal",
    details,
  };
}
