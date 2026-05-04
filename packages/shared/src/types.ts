/** Shared type definitions for ColorForge AI */

export type BookStateType =
  | "PLANNED"
  | "GENERATING"
  | "VALIDATING"
  | "LISTING"
  | "PUBLISHING"
  | "LIVE"
  | "KILLED"
  | "PAUSED";

export type PolicyStatusType = "PROPOSED" | "APPROVED" | "RETIRED" | "REJECTED";

export type ValidationVerdict = "pass" | "fail" | "needs_regen";

export type RecommendedAction = "publish" | "regenerate_pages" | "kill";

export type DetailTier = "sparse" | "medium" | "dense";

export type BookClassification = "winner" | "flat" | "loser";

export type AlertSeverity = "info" | "warning" | "critical";

export type AgentName =
  | "niche_hunter"
  | "deep_scout"
  | "strategist"
  | "generator"
  | "critic"
  | "seo"
  | "publisher"
  | "performance_monitor";

export type SuccessWindow = 7 | 14 | 30;
