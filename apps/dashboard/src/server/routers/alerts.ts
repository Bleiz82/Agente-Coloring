import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "@/server/trpc";

export const alertsRouter = createTRPCRouter({
  list: protectedProcedure
    .input(
      z.object({
        acknowledged: z.boolean().optional(),
        severity: z.string().optional(),
        limit: z.number().int().min(1).max(100).default(50),
      }),
    )
    .query(async ({ ctx, input }) => {
      const where: Record<string, unknown> = {};
      if (input.acknowledged !== undefined) {
        where.acknowledged = input.acknowledged;
      }
      if (input.severity !== undefined) {
        where.severity = input.severity;
      }

      return ctx.prisma.alert.findMany({
        where,
        orderBy: { createdAt: "desc" },
        take: input.limit,
      });
    }),

  acknowledge: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.alert.update({
        where: { id: input.id },
        data: { acknowledged: true, ackedAt: new Date() },
      });
    }),

  acknowledgeAll: protectedProcedure.mutation(async ({ ctx }) => {
    const result = await ctx.prisma.alert.updateMany({
      where: { acknowledged: false },
      data: { acknowledged: true, ackedAt: new Date() },
    });
    return { count: result.count };
  }),
});
