"use client";

import { useEffect, useState } from "react";
import StatusBeacon from "@/components/ui/StatusBeacon";
import type { BeaconState } from "@/lib/health-engine";

interface BeaconData {
  state: BeaconState;
  humanMessage: string;
}

export function SystemBeaconMini() {
  const [data, setData] = useState<BeaconData>({
    state: "GREEN",
    humanMessage: "Loading...",
  });

  useEffect(() => {
    async function fetchBeacon() {
      try {
        const res = await fetch("/api/health/beacon");
        if (res.ok) {
          const json = (await res.json()) as BeaconData;
          setData(json);
        }
      } catch {
        setData({ state: "BLACK", humanMessage: "Connection lost" });
      }
    }

    void fetchBeacon();
  }, []);

  return <StatusBeacon state={data.state} size="sm" label={data.humanMessage} />;
}
