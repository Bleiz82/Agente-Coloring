import { z } from "zod";

export const ListingSchema = z.object({
  bookId: z.string().uuid(),
  title: z.string().min(1).max(200),
  subtitle: z.string().max(200).optional(),
  keywords: z.array(z.string().max(50)).length(7),
  descriptionHtml: z.string().max(4000),
  bisacCodes: z.array(z.string()).min(1).max(3),
  priceUsd: z.number().positive().min(0.99).max(250),
  priceEur: z.number().positive().optional(),
  priceGbp: z.number().positive().optional(),
  aiDisclosure: z.literal(true),
  publicationTargetDate: z.string().datetime().optional(),
});

export type Listing = z.infer<typeof ListingSchema>;

export const listingExample: Listing = {
  bookId: "770e8400-e29b-41d4-a716-446655440002",
  title: "Ocean Mandala Coloring Book for Adults: 75 Relaxing Sea-Themed Designs",
  subtitle:
    "Stress Relief Coloring with Intricate Ocean Waves, Seashells & Coral Mandalas - Perfect Gift for Women and Teens",
  keywords: [
    "ocean coloring book adults",
    "mandala coloring book stress relief",
    "sea themed adult coloring",
    "relaxation coloring pages women",
    "intricate mandala designs",
    "ocean wave patterns coloring",
    "gift coloring book teens adults",
  ],
  descriptionHtml:
    "<b>Dive Into Calm with 75 Stunning Ocean Mandalas</b><br><br>Escape the everyday and immerse yourself in the tranquil beauty of the sea. Each page features a unique hand-crafted mandala design blending ocean elements — flowing waves, delicate seashells, intricate coral — with geometric precision.<br><br>&#10026; 75 completely unique designs — no duplicates<br>&#10026; Bold, thick lines designed for stress-free coloring<br>&#10026; Single-sided pages to prevent bleed-through<br>&#10026; Suitable for markers, colored pencils, and gel pens<br>&#10026; Perfect gift for birthdays, holidays, or self-care<br><br><b>AI-Generated Content Disclosure:</b> Images in this book were created with AI assistance.",
  bisacCodes: ["ART015000", "CRA019000"],
  priceUsd: 7.99,
  priceEur: 7.49,
  priceGbp: 6.49,
  aiDisclosure: true,
  publicationTargetDate: "2026-05-05T00:00:00.000Z",
};
