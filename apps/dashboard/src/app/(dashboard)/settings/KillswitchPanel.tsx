"use client";

import KillswitchButton from "@/components/ui/KillswitchButton";
import { trpc } from "@/lib/trpc-provider";

export default function KillswitchPanel() {
  const statusQuery = trpc.killswitch.status.useQuery(undefined, {
    refetchInterval: 10_000,
  });

  const activateMutation = trpc.killswitch.activate.useMutation({
    onSuccess: () => {
      void statusQuery.refetch();
    },
  });

  const deactivateMutation = trpc.killswitch.deactivate.useMutation({
    onSuccess: () => {
      void statusQuery.refetch();
    },
  });

  const active = statusQuery.data?.active ?? false;
  const loading = statusQuery.isLoading;
  const mutating =
    activateMutation.isPending || deactivateMutation.isPending;

  return (
    <div
      className="rounded-xl border p-5"
      style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
    >
      <h2 className="mb-1 text-lg font-semibold" style={{ color: "#F4F4F5" }}>
        Killswitch
      </h2>
      <p className="mb-4 text-sm" style={{ color: "#A1A1AA" }}>
        {active
          ? `ACTIVE — ${statusQuery.data?.reason ?? "No reason provided"}`
          : "System is operating normally. Activate to halt all publishing."}
      </p>
      {loading ? (
        <div
          className="h-10 w-48 animate-pulse rounded-lg"
          style={{ backgroundColor: "#27272A" }}
        />
      ) : (
        <KillswitchButton
          active={active}
          onActivate={(reason) => {
            activateMutation.mutate({ reason });
          }}
          onDeactivate={() => {
            deactivateMutation.mutate();
          }}
          disabled={mutating}
        />
      )}
    </div>
  );
}
