"use client";

import { formatRelativeTime } from "@/lib/format";

interface Book {
  id: string;
  asin?: string | null;
  brandAuthor: string;
  state: string;
  pageCount?: number | null;
  createdAt: string | Date;
  publishedAt?: string | Date | null;
}

interface BookTableProps {
  books: Book[];
  onRowClick?: (id: string) => void;
}

const STATE_STYLES: Record<string, { bg: string; text: string }> = {
  LIVE: { bg: "rgba(16,185,129,0.15)", text: "#6EE7B7" },
  PUBLISHING: { bg: "rgba(14,165,233,0.15)", text: "#7DD3FC" },
  KILLED: { bg: "rgba(220,38,38,0.15)", text: "#FCA5A5" },
  PAUSED: { bg: "rgba(113,113,122,0.15)", text: "#A1A1AA" },
};

const DEFAULT_STATE_STYLE = { bg: "rgba(245,158,11,0.15)", text: "#FCD34D" };

export default function BookTable({ books, onRowClick }: BookTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "#27272A" }}>
      <table className="w-full text-left text-sm">
        <thead>
          <tr style={{ backgroundColor: "#18181B" }}>
            {["ASIN", "Author", "State", "Pages", "Created", "Published"].map(
              (header) => (
                <th
                  key={header}
                  className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "#A1A1AA", borderBottom: "1px solid #27272A" }}
                >
                  {header}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {books.map((book) => {
            const stateStyle: { bg: string; text: string } = STATE_STYLES[book.state] ?? DEFAULT_STATE_STYLE;
            return (
              <tr
                key={book.id}
                onClick={() => onRowClick?.(book.id)}
                className={`transition-colors ${onRowClick != null ? "cursor-pointer hover:bg-white/5" : ""}`}
                style={{ borderBottom: "1px solid #27272A" }}
              >
                <td className="px-4 py-3 font-mono text-xs" style={{ color: "#F4F4F5" }}>
                  {book.asin ?? "—"}
                </td>
                <td className="px-4 py-3" style={{ color: "#F4F4F5" }}>
                  {book.brandAuthor}
                </td>
                <td className="px-4 py-3">
                  <span
                    className="rounded-full px-2 py-0.5 text-xs font-semibold"
                    style={{ backgroundColor: stateStyle.bg, color: stateStyle.text }}
                  >
                    {book.state}
                  </span>
                </td>
                <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>
                  {book.pageCount ?? "—"}
                </td>
                <td className="px-4 py-3 text-xs" style={{ color: "#71717A" }}>
                  {formatRelativeTime(book.createdAt)}
                </td>
                <td className="px-4 py-3 text-xs" style={{ color: "#71717A" }}>
                  {book.publishedAt != null ? formatRelativeTime(book.publishedAt) : "—"}
                </td>
              </tr>
            );
          })}
          {books.length === 0 && (
            <tr>
              <td
                colSpan={6}
                className="px-4 py-8 text-center text-sm"
                style={{ color: "#71717A" }}
              >
                No books found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
