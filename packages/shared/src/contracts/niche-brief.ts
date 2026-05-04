import { z } from "zod";

const PainPointSchema = z.object({
  text: z.string(),
  sourceReviewIds: z.array(z.string()),
  severity: z.number().int().min(1).max(5),
  category: z.string(),
});

const StyleClassificationSchema = z.object({
  name: z.string(),
  prevalence: z.number().min(0).max(100),
  examples: z.array(z.string()),
});

const DifferentiatorSchema = z.object({
  description: z.string(),
  rationale: z.string(),
  estimatedImpact: z.enum(["low", "medium", "high"]),
});

export const NicheBriefSchema = z.object({
  nicheId: z.string().uuid(),
  categoryPath: z.array(z.string()).min(1),
  primaryKeyword: z.string().min(1),
  profitabilityScore: z.number().min(0).max(100),
  painPoints: z.array(PainPointSchema),
  styleClassifications: z.array(StyleClassificationSchema),
  differentiators: z.array(DifferentiatorSchema),
  visionAnalysisSummary: z.string(),
  qdrantVectorId: z.string().optional(),
  createdAt: z.string().datetime(),
});

export type NicheBrief = z.infer<typeof NicheBriefSchema>;

export const nicheBriefExample: NicheBrief = {
  nicheId: "550e8400-e29b-41d4-a716-446655440000",
  categoryPath: ["Books", "Crafts, Hobbies & Home", "Coloring Books for Grown-Ups", "Mandala"],
  primaryKeyword: "ocean mandala coloring book",
  profitabilityScore: 68.4,
  painPoints: [
    {
      text: "Lines are too thin and bleed through the page",
      sourceReviewIds: ["rev-001", "rev-015", "rev-023"],
      severity: 4,
      category: "line_quality",
    },
    {
      text: "Only 30 unique designs, rest are duplicates",
      sourceReviewIds: ["rev-008", "rev-042"],
      severity: 3,
      category: "subject_variety",
    },
  ],
  styleClassifications: [
    { name: "geometric-mandala", prevalence: 65, examples: ["B0EX01", "B0EX02"] },
    { name: "organic-floral-mandala", prevalence: 25, examples: ["B0EX03"] },
    { name: "zentangle-hybrid", prevalence: 10, examples: ["B0EX04"] },
  ],
  differentiators: [
    {
      description: "Use thick bold lines (2-3px) to prevent bleed-through complaints",
      rationale: "Top pain point in 1-2 star reviews is thin lines bleeding through",
      estimatedImpact: "high",
    },
    {
      description: "Include 75 unique ocean-themed mandalas with no duplicates",
      rationale: "Duplicate content is second most common complaint",
      estimatedImpact: "medium",
    },
    {
      description: "Blend geometric with organic ocean elements (waves, shells, coral)",
      rationale: "Pure geometric dominates; organic hybrid is underrepresented at 25%",
      estimatedImpact: "medium",
    },
  ],
  visionAnalysisSummary:
    "Dominant style is geometric mandala with thin lines. Market gap exists for bold-line organic-geometric hybrids with ocean themes. Cover palettes trend toward blue-teal with gold accents.",
  qdrantVectorId: "vec-niche-001",
  createdAt: "2026-04-29T03:30:00.000Z",
};
