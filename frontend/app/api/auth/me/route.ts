import { NextResponse } from "next/server"

export async function GET() {
  // In production, this would validate HttpOnly cookie session
  // and return authenticated user from session store

  // Mock implementation returns demo user
  const user = {
    id: "1",
    email: "demo@devgodzilla.dev",
    name: "Demo User",
    role: "admin",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=demo",
    scopes: ["read:projects", "write:projects", "read:protocols", "write:protocols"],
  }

  return NextResponse.json(user)
}
