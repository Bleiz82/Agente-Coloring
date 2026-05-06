"use client";

import { BEACON_COLORS } from "@/lib/colors";
import type { BeaconState } from "@/lib/health-engine";

interface StatusBeaconProps {
  state: BeaconState;
  size?: "sm" | "md" | "lg";
  label?: string;
  pulse?: boolean;
  className?: string;
}

const SIZE_PX: Record<"sm" | "md" | "lg", number> = {
  sm: 12,
  md: 16,
  lg: 24,
};

export default function StatusBeacon({
  state,
  size = "md",
  label,
  pulse,
  className,
}: StatusBeaconProps) {
  const px = SIZE_PX[size];
  const colors = BEACON_COLORS[state];
  const shouldPulse =
    (pulse === undefined ? state !== "GREEN" : pulse) && state !== "GREEN";

  return (
    <span
      className={`inline-flex items-center gap-2 ${className ?? ""}`}
    >
      <span
        className={`rounded-full ring-2 ring-offset-1 ${shouldPulse ? "animate-pulse" : ""}`}
        style={{
          width: px,
          height: px,
          backgroundColor: colors.bg,
          boxShadow: `0 0 ${px / 2}px ${colors.glow}`,
          // ring color via outline since ring-[color] needs Tailwind JIT
          outlineColor: colors.ring,
          // Use CSS custom properties for ring color
          ["--tw-ring-color" as string]: colors.ring,
        }}
        aria-label={label ?? state}
        role="status"
      />
      {label != null && (
        <span className="text-sm text-zinc-300">{label}</span>
      )}
    </span>
  );
}
