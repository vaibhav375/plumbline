import { RoleBadge } from "@/components/RoleBadge";
import { Button } from "@/components/ui/button";
import { supabaseServer } from "@/lib/supabase/server";

import { signOut } from "../login/actions";
import { CheckForm } from "./CheckForm";

export default async function CheckPage() {
  const supabase = await supabaseServer();
  const { data } = await supabase.auth.getClaims();
  const { data: profile } = await supabase
    .from("profiles")
    .select("display_name, role")
    .eq("user_id", data?.claims?.sub ?? "")
    .maybeSingle();
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Check content</h1>
          <p className="text-sm text-muted-foreground">
            Paste a draft or upload a file. Plumbline checks it against Aurelle&apos;s rules and facts, and shows what it
            couldn&apos;t check.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {profile && <RoleBadge name={profile.display_name} role={profile.role} />}
          <form action={signOut}>
            <Button type="submit" variant="ghost" size="sm">
              Sign out
            </Button>
          </form>
        </div>
      </header>
      <CheckForm />
    </main>
  );
}
