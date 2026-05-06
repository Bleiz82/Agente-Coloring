"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        headers: { "Content-Type": "application/json" },
      });

      if (res.ok) {
        router.push("/");
      } else {
        const data: { error?: string } = await res.json() as { error?: string };
        setError(data.error ?? "Login failed");
      }
    } catch {
      setError("Network error — please try again");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {error != null && (
        <div
          className="rounded-md px-3 py-2 text-sm"
          style={{ backgroundColor: "rgba(220,38,38,0.15)", color: "#FCA5A5" }}
        >
          {error}
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="email"
          className="text-sm font-medium"
          style={{ color: "#A1A1AA" }}
        >
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
          style={{
            backgroundColor: "#09090B",
            borderColor: "#27272A",
            color: "#F4F4F5",
          }}
          placeholder="admin@colorforge.ai"
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="password"
          className="text-sm font-medium"
          style={{ color: "#A1A1AA" }}
        >
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
          style={{
            backgroundColor: "#09090B",
            borderColor: "#27272A",
            color: "#F4F4F5",
          }}
          placeholder="********"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="mt-2 rounded-md px-4 py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        style={{ backgroundColor: "#8B5CF6" }}
      >
        {loading ? "Signing in..." : "Sign In"}
      </button>
    </form>
  );
}
