import { z } from "zod";

const PageFlagSchema = z.object({
  pageIndex: z.number().int().nonnegative(),
  type: z.enum([
    "text_contamination",
    "shading_detected",
    "color_detected",
    "double_lines",
    "anatomy_malformed",
    "composition_off_center",
    "subject_too_small",
    "watermark_detected",
    "artifact_detected",
    "prompt_mismatch",
  ]),
  severity: z.number().int().min(1).max(5),
  detail: z.string(),
});

const CoverAssessmentSchema = z.object({
  readabilityScore: z.number().int().min(0).max(100),
  issues: z.array(z.string()),
});

export const ValidationReportSchema = z.object({
  bookId: z.string().uuid(),
  verdict: z.enum(["pass", "fail", "needs_regen"]),
  perPageFlags: z.array(z.array(PageFlagSchema)),
  coverAssessment: CoverAssessmentSchema,
  pdfSpecCompliance: z.boolean(),
  pdfSpecDetails: z.array(z.string()),
  recommendedAction: z.enum(["publish", "regenerate_pages", "kill"]),
  criticModelVersion: z.string(),
});

export type ValidationReport = z.infer<typeof ValidationReportSchema>;

export const validationReportExample: ValidationReport = {
  bookId: "770e8400-e29b-41d4-a716-446655440002",
  verdict: "pass",
  perPageFlags: [
    [],
    [
      {
        pageIndex: 1,
        type: "composition_off_center",
        severity: 2,
        detail: "Subject slightly left of center, minor issue",
      },
    ],
  ],
  coverAssessment: {
    readabilityScore: 85,
    issues: [],
  },
  pdfSpecCompliance: true,
  pdfSpecDetails: [],
  recommendedAction: "publish",
  criticModelVersion: "claude-sonnet-4-6-20260301",
};
