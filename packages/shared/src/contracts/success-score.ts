import { z } from "zod";

export const SuccessScoreSchema = z.object({
  bookId: z.string().uuid(),
  windowDays: z.union([z.literal(7), z.literal(14), z.literal(30)]),
  unitsSold: z.number().int().nonnegative(),
  royaltyTotal: z.number().nonnegative(),
  kenpRead: z.number().int().nonnegative(),
  refundCount: z.number().int().nonnegative(),
  computedScore: z.number().min(0).max(100),
  classification: z.enum(["winner", "flat", "loser"]),
  percentileWithinAccount: z.number().min(0).max(100),
  percentileWithinNiche: z.number().min(0).max(100),
});

export type SuccessScore = z.infer<typeof SuccessScoreSchema>;

export const successScoreExample: SuccessScore = {
  bookId: "770e8400-e29b-41d4-a716-446655440002",
  windowDays: 30,
  unitsSold: 47,
  royaltyTotal: 84.32,
  kenpRead: 1250,
  refundCount: 1,
  computedScore: 78,
  classification: "winner",
  percentileWithinAccount: 92,
  percentileWithinNiche: 88,
};
