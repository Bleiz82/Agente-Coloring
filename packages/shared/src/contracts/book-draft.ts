import { z } from "zod";

const DraftPageSchema = z.object({
  index: z.number().int().nonnegative(),
  imagePath: z.string(),
  promptUsed: z.string(),
  validationStatus: z.enum(["pending", "pass", "warn", "fail"]),
});

const GenerationMetadataSchema = z.object({
  generatorModelVersion: z.string(),
  totalGenerationTimeMs: z.number().int().nonnegative(),
  totalCostUsd: z.number().nonnegative(),
  pagesGenerated: z.number().int().nonnegative(),
  pagesRegenerated: z.number().int().nonnegative(),
});

export const BookDraftSchema = z.object({
  bookId: z.string().uuid(),
  manuscriptPdfPath: z.string().min(1),
  coverPdfPath: z.string().min(1),
  pages: z.array(DraftPageSchema).min(1),
  spineWidthInches: z.number().positive(),
  totalPages: z.number().int().positive(),
  generationMetadata: GenerationMetadataSchema,
});

export type BookDraft = z.infer<typeof BookDraftSchema>;

export const bookDraftExample: BookDraft = {
  bookId: "770e8400-e29b-41d4-a716-446655440002",
  manuscriptPdfPath: "/var/colorforge/assets/stefano-main/770e8400/manuscript.pdf",
  coverPdfPath: "/var/colorforge/assets/stefano-main/770e8400/cover.pdf",
  pages: [
    {
      index: 0,
      imagePath: "/var/colorforge/assets/stefano-main/770e8400/pages/page_000.png",
      promptUsed:
        "Black and white coloring book line art for adults. Subject: intricate ocean wave mandala...",
      validationStatus: "pass",
    },
    {
      index: 1,
      imagePath: "/var/colorforge/assets/stefano-main/770e8400/pages/page_001.png",
      promptUsed:
        "Black and white coloring book line art for adults. Subject: circular mandala with seahorse motifs...",
      validationStatus: "pass",
    },
  ],
  spineWidthInches: 0.169,
  totalPages: 75,
  generationMetadata: {
    generatorModelVersion: "gemini-3-1-flash-image",
    totalGenerationTimeMs: 900000,
    totalCostUsd: 2.93,
    pagesGenerated: 75,
    pagesRegenerated: 3,
  },
};
