"use client";

import { useRouter } from "next/navigation";
import AlertRow from "@/components/ui/AlertRow";
import { trpc } from "@/lib/trpc-provider";

interface Alert {
  id: string;
  severity: string;
  title: string;
  message: string;
  createdAt: string | Date;
  acknowledged: boolean;
}

interface AlertsListProps {
  alerts: Alert[];
}

export default function AlertsList({ alerts }: AlertsListProps) {
  const router = useRouter();
  const acknowledgeMutation = trpc.alerts.acknowledge.useMutation({
    onSuccess: () => {
      router.refresh();
    },
  });

  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <AlertRow
          key={alert.id}
          alert={alert}
          onAcknowledge={(id) => {
            acknowledgeMutation.mutate({ id });
          }}
        />
      ))}
    </div>
  );
}
