import Link from "next/link";
import { SystemBeaconMini } from "@/components/ui/SystemBeaconMini";

interface NavItem {
  href: string;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview", icon: "▦" },
  { href: "/books", label: "Books", icon: "▣" },
  { href: "/performance", label: "Performance", icon: "▲" },
  { href: "/niches", label: "Niches", icon: "◉" },
  { href: "/alerts", label: "Alerts", icon: "◆" },
  { href: "/policies", label: "Policies", icon: "○" },
  { href: "/accounts", label: "Accounts", icon: "●" },
  { href: "/ledger", label: "Ledger", icon: "□" },
  { href: "/settings", label: "Settings", icon: "⚙" },
  { href: "/research", label: "Research", icon: "◎" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen" style={{ backgroundColor: "#09090B" }}>
      {/* Sidebar */}
      <aside
        className="fixed left-0 top-0 z-30 flex h-full w-64 flex-col border-r"
        style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
      >
        <div className="flex h-16 items-center px-6">
          <span className="text-lg font-bold" style={{ color: "#8B5CF6" }}>
            ColorForge AI
          </span>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-2">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-white/5"
              style={{ color: "#A1A1AA" }}
            >
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div
          className="border-t px-6 py-4"
          style={{ borderColor: "#27272A" }}
        >
          <p className="text-xs font-medium" style={{ color: "#A1A1AA" }}>
            ColorForge AI
          </p>
          <p className="text-xs" style={{ color: "#52525B" }}>
            v0.7.0
          </p>
        </div>
      </aside>

      {/* Topbar */}
      <header
        className="fixed left-64 right-0 top-0 z-20 flex h-16 items-center justify-between border-b px-6"
        style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
      >
        <div />
        <SystemBeaconMini />
      </header>

      {/* Main content */}
      <main className="ml-64 mt-16 p-6">{children}</main>
    </div>
  );
}
