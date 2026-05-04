import { z } from "zod";

const PagePromptSchema = z.object({
  index: z.number().int().nonnegative(),
  prompt: z.string().min(1),
  complexityTier: z.enum(["sparse", "medium", "dense"]),
  theme: z.string(),
});

const CoverBriefSchema = z.object({
  subject: z.string(),
  styleFingerprint: z.string(),
  paletteHint: z.string(),
  backgroundHint: z.string(),
});

export const BookPlanSchema = z.object({
  nicheBriefId: z.string().uuid(),
  accountId: z.string().uuid(),
  styleFingerprint: z.string().min(1),
  pageCount: z.number().int().min(20).max(200),
  pagePrompts: z.array(PagePromptSchema).min(1),
  coverBrief: CoverBriefSchema,
  targetKeyword: z.string().min(1),
  targetPrice: z.number().positive(),
  brandAuthor: z.string().min(1),
  expectedProductionMinutes: z.number().positive().optional(),
});

export type BookPlan = z.infer<typeof BookPlanSchema>;

export const bookPlanExample: BookPlan = {
  nicheBriefId: "550e8400-e29b-41d4-a716-446655440000",
  accountId: "660e8400-e29b-41d4-a716-446655440001",
  styleFingerprint: "stefano-main-mandala-flow",
  pageCount: 75,
  pagePrompts: [
    {
      index: 0,
      prompt:
        "Black and white coloring book line art for adults. Subject: intricate ocean wave mandala with seashells and coral integrated into geometric patterns. Style: clean bold outlines, uniform line weight, NO shading, NO gradients, NO grayscale fill. Background: pure white. Composition: subject centered, fills 80% of frame. Detail level: dense. Aspect: portrait 8.5:11. Negative: no text, no watermarks, no signatures, no shading, no color, no double lines.",
      complexityTier: "dense",
      theme: "ocean-wave-mandala",
    },
    {
      index: 1,
      prompt:
        "Black and white coloring book line art for adults. Subject: circular mandala with seahorse motifs and flowing water patterns. Style: clean bold outlines, uniform line weight, NO shading, NO gradients. Background: pure white. Composition: radially symmetric, fills 80% of frame. Detail level: dense. Aspect: portrait 8.5:11. Negative: no text, no watermarks, no signatures, no shading, no color.",
      complexityTier: "dense",
      theme: "seahorse-mandala",
    },
  ],
  coverBrief: {
    subject: "Majestic ocean mandala with waves, shells, and coral",
    styleFingerprint: "stefano-main-mandala-flow",
    paletteHint: "#1A0033, #003366, #FFD700",
    backgroundHint: "Deep ocean blue gradient with subtle wave texture",
  },
  targetKeyword: "ocean mandala coloring book",
  targetPrice: 7.99,
  brandAuthor: "Stefano Demuru",
  expectedProductionMinutes: 20,
};
