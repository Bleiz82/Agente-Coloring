// ColorForge design system — semantic color tokens

export const COLORS = {
  background: "#09090B",
  surface: "#18181B",
  border: "#27272A",
  textPrimary: "#F4F4F5",
  textSecondary: "#A1A1AA",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#DC2626",
  info: "#0EA5E9",
  accent: "#8B5CF6",
  gold: "#FBBF24",
} as const;

export type ColorKey = keyof typeof COLORS;

export const BEACON_COLORS = {
  GREEN: { bg: "#10B981", ring: "#059669", glow: "rgba(16,185,129,0.3)" },
  YELLOW: { bg: "#F59E0B", ring: "#D97706", glow: "rgba(245,158,11,0.3)" },
  ORANGE: { bg: "#F97316", ring: "#EA580C", glow: "rgba(249,115,22,0.3)" },
  RED: { bg: "#DC2626", ring: "#B91C1C", glow: "rgba(220,38,38,0.35)" },
  BLACK: { bg: "#3F3F46", ring: "#27272A", glow: "rgba(63,63,70,0.2)" },
} as const;

export type BeaconState = keyof typeof BEACON_COLORS;

/** Chart palette — consistent across all Recharts components */
export const CHART_COLORS = {
  royaltyActual: COLORS.gold,
  royaltyProjected: "#71717A",
  royaltyTarget: "#34D399",
  accountA: "#8B5CF6",
  accountB: "#0EA5E9",
  accountC: "#F59E0B",
} as const;
