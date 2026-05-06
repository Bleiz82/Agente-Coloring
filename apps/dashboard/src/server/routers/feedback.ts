import { z } from "zod";
import type { InputJsonValue } from "@prisma/client/runtime/library";
import { createTRPCRouter, protectedProcedure } from "@/server/trpc";

export const feedbackRouter = createTRPCRouter({
  log: protectedProcedure
    .input(
      z.object({
        actionType: z.string(),
        targetType: z.string().optional(),
        targetId: z.string().optional(),
        beforeState: z.unknown().optional(),
        afterState: z.unknown().optional(),
        note: z.string().optional(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const actorId = ctx.session.userId ?? "owner";

      const event = await ctx.prisma.feedbackEvent.create({
        data: {
          actorId,
          actionType: input.actionType,
          targetType: input.targetType,
          targetId: input.targetId,
          beforeState: input.beforeState as InputJsonValue | undefined,
          afterState: input.afterState as InputJsonValue | undefined,
          note: input.note,
        },
        select: {
          id: true,
          createdAt: true,
        },
      });

      return event;
    }),

  list: protectedProcedure
    .input(
      z.object({
        actionType: z.string().optional(),
        limit: z.number().int().min(1).max(200).default(50),
      }),
    )
    .query(async ({ ctx, input }) => {
      const where: Record<string, unknown> = {};
      if (input.actionType !== undefined) {
        where.actionType = input.actionType;
      }

      return ctx.prisma.feedbackEvent.findMany({
        where,
        select: {
          id: true,
          actorId: true,
          actionType: true,
          targetType: true,
          targetId: true,
          note: true,
          createdAt: true,
        },
        orderBy: { createdAt: "desc" },
        take: input.limit,
      });
    }),
});
