"use server";

import { redirect } from "next/navigation";

import { supabaseServer } from "@/lib/supabase/server";

// Seeded demo accounts (supabase/seed/aurelle/users.json). The shared password lives only in
// the server environment (DEMO_USER_PASSWORD) and never reaches the browser bundle.
const DEMO_USERS = {
  creator: "asha@aurelle.example",
  agency: "sana@agency.example",
  reviewer: "meera@aurelle.example",
  compliance: "arjun@aurelle.example",
  brand_owner: "kabir@aurelle.example",
} as const;

export type DemoRole = keyof typeof DEMO_USERS;

export async function signInAs(role: DemoRole) {
  const email = DEMO_USERS[role];
  const password = process.env.DEMO_USER_PASSWORD;
  if (!email || !password) redirect("/login?error=config");
  const supabase = await supabaseServer();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) redirect("/login?error=signin");
  redirect("/check");
}

export async function signOut() {
  const supabase = await supabaseServer();
  await supabase.auth.signOut();
  redirect("/login");
}
