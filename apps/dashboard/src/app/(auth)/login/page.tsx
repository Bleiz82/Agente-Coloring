import type { Metadata } from "next";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = {
  title: "Login — ColorForge AI",
};

export default async function LoginPage() {
  const session = await getSession();
  if (session) {
    redirect("/");
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ backgroundColor: "#09090B" }}
    >
      <div
        className="w-full max-w-sm rounded-xl border p-8"
        style={{
          backgroundColor: "#18181B",
          borderColor: "#27272A",
        }}
      >
        <h1
          className="mb-1 text-center text-2xl font-bold"
          style={{ color: "#8B5CF6" }}
        >
          ColorForge AI
        </h1>
        <p
          className="mb-8 text-center text-sm"
          style={{ color: "#A1A1AA" }}
        >
          Mission Control
        </p>
        <LoginForm />
      </div>
    </div>
  );
}
