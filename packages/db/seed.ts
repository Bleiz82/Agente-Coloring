import { PrismaClient } from "@prisma/client";

const db = new PrismaClient();

async function main() {
  console.log("Seeding ColorForge DB...");

  // 3 accounts (matching Stefano's setup)
  const accounts = await Promise.all([
    db.account.upsert({
      where: { label: "stefano-main" },
      update: {},
      create: {
        label: "stefano-main",
        brandAuthors: ["Stefano Demuru", "SD Press"],
        nicheSpecialization: ["mandala-adult", "mindfulness"],
        storageStatePath: "/run/colorforge/state/stefano-main.json",
        proxyEndpointId: "smartproxy-it-01",
        fingerprint: {
          userAgent:
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
          viewport: { width: 1440, height: 900 },
          locale: "it-IT",
          timezone: "Europe/Rome",
          screen: { width: 1440, height: 900 },
        },
        countryCode: "IT",
        dailyQuota: 5,
      },
    }),
    db.account.upsert({
      where: { label: "stefano-secondary" },
      update: {},
      create: {
        label: "stefano-secondary",
        brandAuthors: ["Marco Lussu"],
        nicheSpecialization: ["kids-educational", "seasonal"],
        storageStatePath: "/run/colorforge/state/stefano-secondary.json",
        proxyEndpointId: "smartproxy-it-02",
        fingerprint: {
          userAgent:
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
          viewport: { width: 1920, height: 1080 },
          locale: "it-IT",
          timezone: "Europe/Rome",
          screen: { width: 1920, height: 1080 },
        },
        countryCode: "IT",
        dailyQuota: 5,
      },
    }),
    db.account.upsert({
      where: { label: "sister" },
      update: {},
      create: {
        label: "sister",
        brandAuthors: ["Giulia D."],
        nicheSpecialization: ["floral", "wellness-women"],
        storageStatePath: "/run/colorforge/state/sister.json",
        proxyEndpointId: "smartproxy-it-03",
        fingerprint: {
          userAgent:
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
          viewport: { width: 1366, height: 768 },
          locale: "it-IT",
          timezone: "Europe/Rome",
          screen: { width: 1366, height: 768 },
        },
        countryCode: "IT",
        dailyQuota: 5,
      },
    }),
  ]);

  console.log(`${accounts.length} accounts ready`);

  // Sample niche for testing
  const niche = await db.niche.create({
    data: {
      categoryPath: ["Books", "Crafts, Hobbies & Home", "Coloring Books for Grown-Ups", "Mandala"],
      primaryKeyword: "ocean mandala coloring book",
      rawObservations: {
        topCompetitors: [],
        scannedAt: new Date().toISOString(),
      },
      signals: {
        demand: 0.72,
        price: 0.65,
        competition: 0.45,
        qualityGap: 0.8,
        trend: 0.55,
        seasonality: 0.9,
        catalogFit: 0.85,
        saturation: 0.4,
      },
      profitabilityScore: 68.4,
      scanRunId: crypto.randomUUID(),
    },
  });
  console.log(`Sample niche: ${niche.primaryKeyword}`);

  // Initial seed policies (anti-cold-start)
  await db.policy.createMany({
    data: [
      {
        ruleText: "Coloring book covers MUST remain readable at 200px thumbnail size",
        ruleMachineReadable: {
          type: "cover_constraint",
          check: "thumbnail_readability_min_score",
          value: 70,
        },
        appliesTo: ["generator", "critic"],
        confidenceScore: 100,
        supportingEvidence: [],
        status: "APPROVED",
        approvedAt: new Date(),
      },
      {
        ruleText:
          "Every prompt for line-art MUST include 'no shading, no gradients, uniform line weight'",
        ruleMachineReadable: {
          type: "prompt_constraint",
          required_phrases: ["no shading", "no gradients", "uniform line weight"],
        },
        appliesTo: ["generator"],
        confidenceScore: 100,
        supportingEvidence: [],
        status: "APPROVED",
        approvedAt: new Date(),
      },
      {
        ruleText: "AI Content Disclosure flag MUST be true on every KDP submission",
        ruleMachineReadable: {
          type: "publish_constraint",
          field: "ai_disclosure",
          value: true,
        },
        appliesTo: ["publisher", "seo"],
        confidenceScore: 100,
        supportingEvidence: [],
        status: "APPROVED",
        approvedAt: new Date(),
      },
    ],
  });
  console.log("3 initial policies seeded");

  console.log("Seed complete");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await db.$disconnect();
  });
