"use client";

import { useState } from "react";

interface KillswitchButtonProps {
  active: boolean;
  onActivate: (reason: string) => void;
  onDeactivate: () => void;
  disabled?: boolean;
}

export default function KillswitchButton({
  active,
  onActivate,
  onDeactivate,
  disabled,
}: KillswitchButtonProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reason, setReason] = useState("");

  function handleConfirm() {
    if (reason.length >= 10) {
      onActivate(reason);
      setDialogOpen(false);
      setReason("");
    }
  }

  if (active) {
    return (
      <button
        type="button"
        onClick={onDeactivate}
        disabled={disabled}
        className="relative flex items-center gap-2 rounded-lg px-5 py-3 text-sm font-bold text-white transition-opacity disabled:opacity-50"
        style={{ backgroundColor: "#10B981" }}
      >
        <span className="relative flex h-3 w-3">
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
            style={{ backgroundColor: "#DC2626" }}
          />
          <span
            className="relative inline-flex h-3 w-3 rounded-full"
            style={{ backgroundColor: "#DC2626" }}
          />
        </span>
        DEACTIVATE KILLSWITCH
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setDialogOpen(true)}
        disabled={disabled}
        className="rounded-lg px-5 py-3 text-sm font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        style={{ backgroundColor: "#DC2626" }}
      >
        ACTIVATE KILLSWITCH
      </button>

      {dialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div
            className="w-full max-w-md rounded-xl border p-6"
            style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
          >
            <h2 className="mb-1 text-lg font-bold" style={{ color: "#FCA5A5" }}>
              Activate Killswitch
            </h2>
            <p className="mb-4 text-sm" style={{ color: "#A1A1AA" }}>
              This will halt all publishing operations immediately. Please provide a reason.
            </p>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason for activation (min 10 characters)..."
              rows={3}
              className="mb-4 w-full resize-none rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
              style={{
                backgroundColor: "#09090B",
                borderColor: "#27272A",
                color: "#F4F4F5",
              }}
            />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setDialogOpen(false);
                  setReason("");
                }}
                className="flex-1 rounded-md border px-4 py-2 text-sm font-medium transition-colors hover:bg-white/5"
                style={{ borderColor: "#27272A", color: "#A1A1AA" }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={reason.length < 10}
                className="flex-1 rounded-md px-4 py-2 text-sm font-bold text-white transition-opacity disabled:opacity-40"
                style={{ backgroundColor: "#DC2626" }}
              >
                CONFIRM — HALT ALL OPERATIONS
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
