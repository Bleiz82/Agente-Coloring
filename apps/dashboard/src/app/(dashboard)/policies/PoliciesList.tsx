"use client";

import { useRouter } from "next/navigation";
import PolicyCard from "@/components/ui/PolicyCard";
import { trpc } from "@/lib/trpc-provider";

interface Policy {
  id: string;
  ruleText: string;
  appliesTo: string[];
  status: string;
  confidenceScore: number;
  proposedAt: string | Date;
}

interface PoliciesListProps {
  policies: Policy[];
}

export default function PoliciesList({ policies }: PoliciesListProps) {
  const router = useRouter();

  const approveMutation = trpc.policies.approve.useMutation({
    onSuccess: () => {
      router.refresh();
    },
  });

  const rejectMutation = trpc.policies.reject.useMutation({
    onSuccess: () => {
      router.refresh();
    },
  });

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {policies.map((policy) => (
        <PolicyCard
          key={policy.id}
          policy={policy}
          onApprove={(id) => {
            approveMutation.mutate({ id });
          }}
          onReject={(id) => {
            rejectMutation.mutate({ id });
          }}
        />
      ))}
    </div>
  );
}
