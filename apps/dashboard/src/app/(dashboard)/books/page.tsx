import type { Metadata } from "next";
import BookTable from "@/components/ui/BookTable";
import { prisma } from "@/lib/prisma";

export const metadata: Metadata = { title: "Books — ColorForge AI" };

async function getBooks() {
  try {
    return await prisma.book.findMany({
      orderBy: { createdAt: "desc" },
      take: 100,
      select: {
        id: true,
        asin: true,
        brandAuthor: true,
        state: true,
        pageCount: true,
        createdAt: true,
        publishedAt: true,
      },
    });
  } catch {
    return [];
  }
}

export default async function BooksPage() {
  const books = await getBooks();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
          Books
        </h1>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ backgroundColor: "rgba(139,92,246,0.15)", color: "#A78BFA" }}
        >
          {books.length}
        </span>
      </div>

      {books.length > 0 ? (
        <BookTable books={books} />
      ) : (
        <div
          className="rounded-xl border p-8 text-center"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm" style={{ color: "#71717A" }}>
            No books yet — start the pipeline to generate your first book.
          </p>
        </div>
      )}
    </div>
  );
}
