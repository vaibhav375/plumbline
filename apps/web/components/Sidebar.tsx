"use client";

import { ClipboardCheck, FileSearch, Gauge, Library, ListChecks, Menu, ScrollText, ShieldCheck, Activity, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Brandmark } from "@/components/Brandmark";
import { SignOutButton } from "@/components/SignOutButton";

const REVIEWERS = new Set(["reviewer", "compliance", "brand_owner", "accessibility", "auditor"]);
const ROLE: Record<string, string> = {
  creator: "Creator",
  external_creator: "Agency",
  reviewer: "Reviewer",
  compliance: "Compliance",
  accessibility: "Accessibility",
  brand_owner: "Brand owner",
  auditor: "Auditor",
};

type Item = { href: string; label: string; hint: string; icon: typeof Gauge; reviewers?: boolean; signedIn?: boolean };
// Similar features sit together; each says in a few words what it is for.
const GROUPS: { name: string; items: Item[] }[] = [
  { name: "Write", items: [{ href: "/check", label: "Check a post", hint: "Find problems before you publish", icon: FileSearch, signedIn: true }] },
  {
    name: "Review",
    items: [
      { href: "/review", label: "Review queue", hint: "Posts waiting for a decision", icon: ListChecks, reviewers: true, signedIn: true },
      { href: "/audit", label: "Audit log", hint: "Every decision, tamper-evident", icon: ScrollText, signedIn: true },
    ],
  },
  {
    name: "Brand rules",
    items: [
      { href: "/rules", label: "Rulebook", hint: "What the checker looks for", icon: Library, signedIn: true },
      { href: "/facts", label: "Facts", hint: "Claims you can make, and their wording", icon: ClipboardCheck, signedIn: true },
      { href: "/health", label: "Guideline health", hint: "Rules reviewers disagree with", icon: Gauge, signedIn: true },
    ],
  },
  {
    name: "Proof",
    items: [
      { href: "/about", label: "How I know it works", hint: "Test results against a baseline", icon: ShieldCheck },
      { href: "/status", label: "Status", hint: "Is everything up right now?", icon: Activity },
    ],
  },
];

export type Profile = { display_name: string; role: string } | null;

function Nav({ profile, onNavigate }: { profile: Profile; onNavigate?: () => void }) {
  const path = usePathname();
  return (
    <nav aria-label="Main" className="space-y-5">
      {GROUPS.map((g) => {
        const items = g.items.filter((i) => (!i.signedIn || profile) && (!i.reviewers || (profile && REVIEWERS.has(profile.role))));
        if (!items.length) return null;
        return (
          <div key={g.name} className="space-y-1">
            <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-white/45">{g.name}</p>
            {items.map(({ href, label, hint, icon: Icon }) => {
              const active = path === href || path.startsWith(href + "/");
              return (
                <Link key={href} href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
                  className={`group flex items-start gap-3 rounded-lg px-3 py-2 transition-colors ${active ? "bg-white/10 text-white" : "text-white/75 hover:bg-white/5 hover:text-white"}`}>
                  <Icon aria-hidden className={`mt-0.5 size-4 shrink-0 ${active ? "text-[#A9A2F7]" : "text-white/50 group-hover:text-white/80"}`} />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{label}</span>
                    <span className="block text-xs text-white/50">{hint}</span>
                  </span>
                </Link>
              );
            })}
          </div>
        );
      })}
    </nav>
  );
}

function Account({ profile }: { profile: Profile }) {
  if (!profile) {
    return <Link href="/login" className="block rounded-lg bg-accent-brand px-3 py-2 text-center text-sm font-medium text-white hover:bg-[#3F34B8]">Sign in to try it</Link>;
  }
  return (
    <div className="space-y-2 rounded-lg bg-white/5 p-3">
      <p className="text-sm text-white/70">
        Signed in as <span className="font-medium text-white">{profile.display_name}</span> · {ROLE[profile.role] ?? profile.role}
      </p>
      <SignOutButton />
    </div>
  );
}

/** Persistent navigation: a dark rail on wide screens, a menu button on phones. */
export function Sidebar({ profile }: { profile: Profile }) {
  const [open, setOpen] = useState(false);
  const brand = (
    <Link href={profile ? "/check" : "/login"} className="flex items-center gap-2.5 text-white">
      <Brandmark className="size-7 text-white/80" />
      <span className="font-display text-lg font-bold tracking-tight">Plumbline</span>
    </Link>
  );
  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col gap-6 overflow-y-auto bg-ink px-3 py-5 lg:flex">
        <div className="px-3">{brand}</div>
        <Nav profile={profile} />
        <div className="mt-auto"><Account profile={profile} /></div>
      </aside>
      <div className="sticky top-0 z-30 flex items-center justify-between bg-ink px-4 py-3 lg:hidden">
        {brand}
        <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="mobile-nav"
          className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium text-white ring-1 ring-white/20">
          {open ? <X className="size-4" aria-hidden /> : <Menu className="size-4" aria-hidden />} Menu
        </button>
      </div>
      {open && (
        <div id="mobile-nav" className="fixed inset-x-0 top-[52px] bottom-0 z-30 space-y-6 overflow-y-auto bg-ink px-3 py-5 lg:hidden">
          <Nav profile={profile} onNavigate={() => setOpen(false)} />
          <Account profile={profile} />
        </div>
      )}
    </>
  );
}
