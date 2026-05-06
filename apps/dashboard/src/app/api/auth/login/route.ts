import { NextResponse } from "next/server";
import { signToken, verifyPassword, COOKIE_NAME } from "@/lib/auth";

interface LoginBody {
  email: string;
  password: string;
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  const { email, password } = body;

  if (!email || !password) {
    return NextResponse.json({ error: "Email and password are required" }, { status: 400 });
  }

  const dashboardEmail = process.env.DASHBOARD_EMAIL;
  const passwordHash = process.env.DASHBOARD_PASSWORD_HASH;

  let authenticated = false;

  if (dashboardEmail && passwordHash) {
    if (email === dashboardEmail) {
      authenticated = await verifyPassword(password, passwordHash);
    }
  } else {
    // Fallback for development
    authenticated = email === "admin@colorforge.ai" && password === "colorforge2025";
  }

  if (!authenticated) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  const token = await signToken({ userId: "owner", email, role: "owner" });

  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });

  return response;
}
