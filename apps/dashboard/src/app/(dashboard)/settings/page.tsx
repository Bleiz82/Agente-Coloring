import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import KillswitchPanel from "./KillswitchPanel";

export const metadata: Metadata = { title: "Settings — ColorForge AI" };

interface ConfigRow {
  id: string;
  key: string;
  value: unknown;
  updatedAt: Date;
  updatedBy: string;
}

interface StateRow {
  id: string;
  key: string;
  value: string;
  reason: string | null;
  activatedAt: Date;
  activatedBy: string;
}

async function getSystemConfig(): Promise<ConfigRow[]> {
  try {
    return await prisma.systemConfig.findMany({
      orderBy: { key: "asc" },
    });
  } catch {
    return [];
  }
}

async function getSystemState(): Promise<StateRow[]> {
  try {
    return await prisma.systemState.findMany({
      orderBy: { key: "asc" },
    });
  } catch {
    return [];
  }
}

export default async function SettingsPage() {
  const [config, state] = await Promise.all([
    getSystemConfig(),
    getSystemState(),
  ]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
        Settings
      </h1>

      {/* Killswitch */}
      <KillswitchPanel />

      {/* System Config */}
      <section>
        <h2
          className="mb-3 text-lg font-semibold"
          style={{ color: "#F4F4F5" }}
        >
          System Configuration
        </h2>
        {config.length > 0 ? (
          <div
            className="overflow-x-auto rounded-xl border"
            style={{ borderColor: "#27272A" }}
          >
            <table className="w-full text-left text-sm">
              <thead>
                <tr style={{ backgroundColor: "#18181B" }}>
                  {["Key", "Value", "Updated By"].map((header) => (
                    <th
                      key={header}
                      className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider"
                      style={{
                        color: "#A1A1AA",
                        borderBottom: "1px solid #27272A",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {config.map((row) => (
                  <tr
                    key={row.id}
                    style={{ borderBottom: "1px solid #27272A" }}
                  >
                    <td
                      className="px-4 py-3 font-mono text-xs"
                      style={{ color: "#F4F4F5" }}
                    >
                      {row.key}
                    </td>
                    <td
                      className="max-w-md truncate px-4 py-3 font-mono text-xs"
                      style={{ color: "#A1A1AA" }}
                    >
                      {JSON.stringify(row.value)}
                    </td>
                    <td
                      className="px-4 py-3 text-xs"
                      style={{ color: "#71717A" }}
                    >
                      {row.updatedBy}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm" style={{ color: "#71717A" }}>
            No configuration entries.
          </p>
        )}
      </section>

      {/* System State */}
      <section>
        <h2
          className="mb-3 text-lg font-semibold"
          style={{ color: "#F4F4F5" }}
        >
          System State
        </h2>
        {state.length > 0 ? (
          <div
            className="overflow-x-auto rounded-xl border"
            style={{ borderColor: "#27272A" }}
          >
            <table className="w-full text-left text-sm">
              <thead>
                <tr style={{ backgroundColor: "#18181B" }}>
                  {["Key", "Value", "Reason", "Activated By"].map((header) => (
                    <th
                      key={header}
                      className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider"
                      style={{
                        color: "#A1A1AA",
                        borderBottom: "1px solid #27272A",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {state.map((row) => (
                  <tr
                    key={row.id}
                    style={{ borderBottom: "1px solid #27272A" }}
                  >
                    <td
                      className="px-4 py-3 font-mono text-xs"
                      style={{ color: "#F4F4F5" }}
                    >
                      {row.key}
                    </td>
                    <td
                      className="px-4 py-3 font-mono text-xs font-semibold"
                      style={{
                        color:
                          row.value === "ACTIVE" ? "#FCA5A5" : "#6EE7B7",
                      }}
                    >
                      {row.value}
                    </td>
                    <td
                      className="px-4 py-3 text-xs"
                      style={{ color: "#A1A1AA" }}
                    >
                      {row.reason ?? "—"}
                    </td>
                    <td
                      className="px-4 py-3 text-xs"
                      style={{ color: "#71717A" }}
                    >
                      {row.activatedBy}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm" style={{ color: "#71717A" }}>
            No state entries.
          </p>
        )}
      </section>
    </div>
  );
}
