import { NextResponse } from "next/server";
import type { BeaconState } from "@/lib/health-engine";

interface BeaconResponse {
  state: BeaconState;
  humanMessage: string;
}

export function GET(): NextResponse<BeaconResponse> {
  return NextResponse.json({
    state: "GREEN",
    humanMessage: "All systems nominal",
  });
}
