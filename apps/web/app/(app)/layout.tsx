import Link from "next/link";

import { type Profile, Sidebar } from "@/components/Sidebar";
import { supabaseServer } from "@/lib/supabase/server";

// Loaded once per visit: layouts stay mounted while you move between pages.
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await supabaseServer();
  const { data } = await supabase.auth.getClaims();
  const sub = data?.claims?.sub;
  const { data: profile } = sub
    ? await supabase.from("profiles").select("display_name, role").eq("user_id", sub).maybeSingle()
    : { data: null };
  return (
    <div className="min-h-dvh">
      <Sidebar profile={(profile as Profile) ?? null} />
      <div className="lg:pl-64">
        {children}
        <footer className="mx-auto flex max-w-6xl flex-wrap gap-x-4 gap-y-1 px-4 pb-8 pt-4 text-sm text-muted-foreground sm:px-6">
          <Link href="/status" className="underline-offset-4 hover:underline">Status</Link>
          <Link href="/about" className="underline-offset-4 hover:underline">How I know it works</Link>
          <span>Aurelle Skin is a fictional brand; no real data is used.</span>
        </footer>
      </div>
    </div>
  );
}
