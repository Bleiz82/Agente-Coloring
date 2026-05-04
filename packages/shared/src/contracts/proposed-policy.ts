import { z } from "zod";

export const ProposedPolicySchema = z.object({
  ruleText: z.string().min(1),
  ruleMachineReadable: z.record(z.unknown()),
  appliesTo: z.array(z.string()).min(1),
  originatingExperimentId: z.string().uuid().optional(),
  confidenceScore: z.number().min(0).max(100),
  supportingEvidence: z.array(z.string().uuid()),
  status: z.enum(["PROPOSED", "APPROVED", "RETIRED", "REJECTED"]),
  proposedAt: z.string().datetime(),
});

export type ProposedPolicy = z.infer<typeof ProposedPolicySchema>;

export const proposedPolicyExample: ProposedPolicy = {
  ruleText:
    "Covers with dark backgrounds (brightness < 30) in mandala niche convert 24% better than light backgrounds",
  ruleMachineReadable: {
    type: "cover_preference",
    niche_filter: "mandala",
    parameter: "cover_brightness",
    operator: "lt",
    value: 30,
    effect_size: 0.24,
  },
  appliesTo: ["strategist", "generator"],
  originatingExperimentId: "880e8400-e29b-41d4-a716-446655440003",
  confidenceScore: 72,
  supportingEvidence: [
    "770e8400-e29b-41d4-a716-446655440002",
    "770e8400-e29b-41d4-a716-446655440005",
    "770e8400-e29b-41d4-a716-446655440008",
  ],
  status: "PROPOSED",
  proposedAt: "2026-06-15T03:00:00.000Z",
};
