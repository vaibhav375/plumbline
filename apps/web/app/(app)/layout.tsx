import Link from "next/link";

import { type Profile, SiteNav } from "@/components/SiteNav";
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
      <SiteNav profile={(profile as Profile) ?? null} />
      <div>
        {children}
        <footer className="mx-auto mt-10 flex max-w-6xl flex-wrap gap-x-6 gap-y-1 border-t border-line px-4 pt-6 pb-10 font-label text-xs uppercase text-bone/50 sm:px-6">
          <Link href="/status" className="underline-offset-4 hover:underline">Status</Link>
          <Link href="/about" className="underline-offset-4 hover:underline">How I know it works</Link>
          <span>Aurelle Skin is a fictional brand; no real data is used.</span>
        </footer>
      </div>
    </div>
  );
}
