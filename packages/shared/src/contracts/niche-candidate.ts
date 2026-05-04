import { z } from "zod";

const CompetitorSnapSchema = z.object({
  asin: z.string(),
  title: z.string(),
  author: z.string(),
  bsr: z.number().int().positive(),
  price: z.number().positive(),
  reviewCount: z.number().int().nonnegative(),
  rating: z.number().min(0).max(5),
  publicationDate: z.string().optional(),
  pageCount: z.number().int().positive().optional(),
});

const ProfitabilityBreakdownSchema = z.object({
  demand: z.number().min(0).max(1),
  price: z.number().min(0).max(1),
  competition: z.number().min(0).max(1),
  qualityGap: z.number().min(0).max(1),
  trend: z.number().min(0).max(1),
  seasonality: z.number().min(0).max(1),
  catalogFit: z.number().min(0).max(1),
  saturation: z.number().min(0).max(1),
  weightedTotal: z.number().min(0).max(100),
});

const TrendSignalSchema = z.object({
  googleTrends90dSlope: z.number(),
  pinterestSearchVelocity: z.number().optional(),
  amazonSuggestCount: z.number().int().nonnegative().optional(),
});

export const NicheCandidateSchema = z.object({
  categoryPath: z.array(z.string()).min(1),
  primaryKeyword: z.string().min(1),
  topCompetitors: z.array(CompetitorSnapSchema),
  profitability: ProfitabilityBreakdownSchema,
  trendSignals: TrendSignalSchema,
  scanTimestamp: z.string().datetime(),
  rawHtmlHashes: z.array(z.string()).optional(),
});

export type NicheCandidate = z.infer<typeof NicheCandidateSchema>;

export const nicheCandidateExample: NicheCandidate = {
  categoryPath: ["Books", "Crafts, Hobbies & Home", "Coloring Books for Grown-Ups", "Mandala"],
  primaryKeyword: "ocean mandala coloring book",
  topCompetitors: [
    {
      asin: "B0EXAMPLE01",
      title: "Ocean Mandala Coloring Book for Adults",
      author: "Jane Artist",
      bsr: 15420,
      price: 7.99,
      reviewCount: 342,
      rating: 4.3,
      publicationDate: "2025-06-15",
      pageCount: 75,
    },
  ],
  profitability: {
    demand: 0.72,
    price: 0.65,
    competition: 0.45,
    qualityGap: 0.8,
    trend: 0.55,
    seasonality: 0.9,
    catalogFit: 0.85,
    saturation: 0.4,
    weightedTotal: 68.4,
  },
  trendSignals: {
    googleTrends90dSlope: 0.12,
    pinterestSearchVelocity: 0.35,
    amazonSuggestCount: 8,
  },
  scanTimestamp: "2026-04-29T02:00:00.000Z",
};
