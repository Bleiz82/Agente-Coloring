import { describe, expect, it } from "vitest";
import {
  BookDraftSchema,
  BookPlanSchema,
  ListingSchema,
  NicheBriefSchema,
  NicheCandidateSchema,
  ProposedPolicySchema,
  SuccessScoreSchema,
  ValidationReportSchema,
  bookDraftExample,
  bookPlanExample,
  listingExample,
  nicheBriefExample,
  nicheCandidateExample,
  proposedPolicyExample,
  successScoreExample,
  validationReportExample,
} from "../index.js";

describe("NicheCandidate contract", () => {
  it("validates the example fixture", () => {
    const result = NicheCandidateSchema.safeParse(nicheCandidateExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(nicheCandidateExample);
    const parsed = NicheCandidateSchema.parse(JSON.parse(json));
    expect(parsed).toEqual(nicheCandidateExample);
  });

  it("rejects invalid data", () => {
    const result = NicheCandidateSchema.safeParse({ categoryPath: [] });
    expect(result.success).toBe(false);
  });
});

describe("NicheBrief contract", () => {
  it("validates the example fixture", () => {
    const result = NicheBriefSchema.safeParse(nicheBriefExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(nicheBriefExample);
    const parsed = NicheBriefSchema.parse(JSON.parse(json));
    expect(parsed).toEqual(nicheBriefExample);
  });

  it("rejects missing required fields", () => {
    const result = NicheBriefSchema.safeParse({ nicheId: "not-a-uuid" });
    expect(result.success).toBe(false);
  });
});

describe("BookPlan contract", () => {
  it("validates the example fixture", () => {
    const result = BookPlanSchema.safeParse(bookPlanExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(bookPlanExample);
    const parsed = BookPlanSchema.parse(JSON.parse(json));
    expect(parsed).toEqual(bookPlanExample);
  });

  it("rejects page count below minimum", () => {
    const invalid = { ...bookPlanExample, pageCount: 5 };
    const result = BookPlanSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

describe("BookDraft contract", () => {
  it("validates the example fixture", () => {
    const result = BookDraftSchema.safeParse(bookDraftExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(bookDraftExample);
    const parsed = BookDraftSchema.parse(JSON.parse(json));
    expect(parsed).toEqual(bookDraftExample);
  });
});

describe("ValidationReport contract", () => {
  it("validates the example fixture", () => {
    const result = ValidationReportSchema.safeParse(validationReportExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(validationReportExample);
    const parsed = ValidationReportSchema.parse(JSON.parse(json));
    expect(parsed).toEqual(validationReportExample);
  });

  it("rejects invalid verdict", () => {
    const invalid = { ...validationReportExample, verdict: "maybe" };
    const result = ValidationReportSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

describe("Listing contract", () => {
  it("validates the example fixture", () => {
    const result = ListingSchema.safeParse(listingExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(listingExample);
    const parsed = ListingSchema.parse(JSON.parse(json));
    expect(parsed).toEqual(listingExample);
  });

  it("enforces exactly 7 keywords", () => {
    const invalid = { ...listingExample, keywords: ["one", "two"] };
    const result = ListingSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });

  it("enforces aiDisclosure must be true", () => {
    const invalid = { ...listingExample, aiDisclosure: false };
    const result = ListingSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

describe("SuccessScore contract", () => {
  it("validates the example fixture", () => {
    const result = SuccessScoreSchema.safeParse(successScoreExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(successScoreExample);
    const parsed = SuccessScoreSchema.parse(JSON.parse(json));
    expect(parsed).toEqual(successScoreExample);
  });

  it("only accepts valid window days", () => {
    const invalid = { ...successScoreExample, windowDays: 15 };
    const result = SuccessScoreSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

describe("ProposedPolicy contract", () => {
  it("validates the example fixture", () => {
    const result = ProposedPolicySchema.safeParse(proposedPolicyExample);
    expect(result.success).toBe(true);
  });

  it("round-trips through JSON serialization", () => {
    const json = JSON.stringify(proposedPolicyExample);
    const parsed = ProposedPolicySchema.parse(JSON.parse(json));
    expect(parsed).toEqual(proposedPolicyExample);
  });

  it("rejects invalid status", () => {
    const invalid = { ...proposedPolicyExample, status: "MAYBE" };
    const result = ProposedPolicySchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});
