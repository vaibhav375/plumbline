import Link from "next/link";

import { signOut } from "@/app/login/actions";
import { RoleBadge } from "@/components/RoleBadge";
import { Button } from "@/components/ui/button";
import { supabaseServer } from "@/lib/supabase/server";

const REVIEWERS = new Set(["reviewer", "compliance", "brand_owner", "accessibility", "auditor"]);

/** Title, a one-line purpose, and navigation that matches the signed-in role. */
export async function AppHeader({ title, subtitle }: { title: string; subtitle: string }) {
  const supabase = await supabaseServer();
  const { data } = await supabase.auth.getClaims();
  const { data: profile } = await supabase
    .from("profiles")
    .select("display_name, role")
    .eq("user_id", data?.claims?.sub ?? "")
    .maybeSingle();
  return (
    <header className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav aria-label="Main" className="flex gap-4 text-sm">
          <Link href="/check" className="underline-offset-4 hover:underline">Check content</Link>
          {profile && REVIEWERS.has(profile.role) && (
            <Link href="/review" className="underline-offset-4 hover:underline">Review queue</Link>
          )}
        </nav>
        <div className="flex items-center gap-3">
          {profile && <RoleBadge name={profile.display_name} role={profile.role} />}
          <form action={signOut}>
            <Button type="submit" variant="ghost" size="sm">Sign out</Button>
          </form>
        </div>
      </div>
      <div>
        <h1 className="text-2xl font-semibold">{title}</h1>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </div>
    </header>
  );
}
