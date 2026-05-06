import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "@/server/trpc";

export const policiesRouter = createTRPCRouter({
  list: protectedProcedure
    .input(
      z.object({
        status: z.string().optional(),
        limit: z.number().int().min(1).max(200).default(50),
      }),
    )
    .query(async ({ ctx, input }) => {
      const where: Record<string, unknown> = {};
      if (input.status !== undefined) {
        where.status = input.status;
      }

      return ctx.prisma.policy.findMany({
        where,
        select: {
          id: true,
          ruleText: true,
          appliesTo: true,
          status: true,
          confidenceScore: true,
          proposedAt: true,
          approvedAt: true,
        },
        orderBy: { proposedAt: "desc" },
        take: input.limit,
      });
    }),

  approve: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.policy.update({
        where: { id: input.id },
        data: { status: "APPROVED", approvedAt: new Date() },
      });
    }),

  reject: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.policy.update({
        where: { id: input.id },
        data: { status: "REJECTED" },
      });
    }),
});
