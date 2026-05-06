import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import { formatRelativeTime } from "@/lib/format";

export const metadata: Metadata = { title: "Accounts — ColorForge AI" };

interface AccountRow {
  id: string;
  label: string;
  brandAuthors: string[];
  active: boolean;
  dailyQuota: number;
  warmingStartedAt: Date;
  countryCode: string;
  createdAt: Date;
  _count: { books: number };
}

async function getAccounts(): Promise<AccountRow[]> {
  try {
    return await prisma.account.findMany({
      orderBy: { createdAt: "desc" },
      select: {
        id: true,
        label: true,
        brandAuthors: true,
        active: true,
        dailyQuota: true,
        warmingStartedAt: true,
        countryCode: true,
        createdAt: true,
        _count: { select: { books: true } },
      },
    });
  } catch {
    return [];
  }
}

export default async function AccountsPage() {
  const accounts = await getAccounts();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
          Accounts
        </h1>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ backgroundColor: "rgba(139,92,246,0.15)", color: "#A78BFA" }}
        >
          {accounts.length}
        </span>
      </div>

      {accounts.length > 0 ? (
        <div
          className="overflow-x-auto rounded-xl border"
          style={{ borderColor: "#27272A" }}
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr style={{ backgroundColor: "#18181B" }}>
                {[
                  "Label",
                  "Country",
                  "Brand Authors",
                  "Status",
                  "Quota",
                  "Books",
                  "Warming Since",
                ].map((header) => (
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
              {accounts.map((account) => (
                <tr
                  key={account.id}
                  style={{ borderBottom: "1px solid #27272A" }}
                >
                  <td
                    className="px-4 py-3 font-medium"
                    style={{ color: "#F4F4F5" }}
                  >
                    {account.label}
                  </td>
                  <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>
                    {account.countryCode}
                  </td>
                  <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>
                    <div className="flex flex-wrap gap-1">
                      {account.brandAuthors.map((author) => (
                        <span
                          key={author}
                          className="rounded px-2 py-0.5 text-xs"
                          style={{
                            backgroundColor: "#27272A",
                            color: "#A1A1AA",
                          }}
                        >
                          {author}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: account.active
                          ? "rgba(16,185,129,0.15)"
                          : "rgba(113,113,122,0.15)",
                        color: account.active ? "#6EE7B7" : "#A1A1AA",
                      }}
                    >
                      {account.active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>
                    {account.dailyQuota}/day
                  </td>
                  <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>
                    {account._count.books}
                  </td>
                  <td
                    className="px-4 py-3 text-xs"
                    style={{ color: "#71717A" }}
                  >
                    {formatRelativeTime(account.warmingStartedAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          className="rounded-xl border p-8 text-center"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm" style={{ color: "#71717A" }}>
            No accounts configured yet.
          </p>
        </div>
      )}
    </div>
  );
}
