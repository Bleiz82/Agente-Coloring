import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export function GET(): Response {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      const interval = setInterval(async () => {
        try {
          const count = await prisma.alert.count({
            where: { acknowledged: false },
          });

          const payload = JSON.stringify({
            count,
            timestamp: new Date().toISOString(),
          });

          controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
        } catch {
          // Swallow errors — SSE should not crash on transient DB issues
        }
      }, 10_000);

      // Send initial event immediately
      void (async () => {
        try {
          const count = await prisma.alert.count({
            where: { acknowledged: false },
          });
          const payload = JSON.stringify({
            count,
            timestamp: new Date().toISOString(),
          });
          controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
        } catch {
          // Swallow
        }
      })();

      // Clean up on cancel
      const originalCancel = stream.cancel.bind(stream);
      stream.cancel = (reason?: unknown) => {
        clearInterval(interval);
        return originalCancel(reason);
      };

      // Also handle controller close via abort
      void new Promise<void>((resolve) => {
        const checkInterval = setInterval(() => {
          try {
            // Test if the controller is still open by trying to enqueue empty
            // This will throw if closed
            controller.enqueue(encoder.encode(""));
          } catch {
            clearInterval(interval);
            clearInterval(checkInterval);
            resolve();
          }
        }, 30_000);
      });
    },
    cancel() {
      // ReadableStream cancel callback — interval cleared via the override above
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
