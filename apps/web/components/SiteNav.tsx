"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

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

type Item = { href: string; label: string; hint: string; reviewers?: boolean; work?: boolean };
// The bar carries the work; the menu adds the proof pages. Similar features sit together.
const GROUPS: { name: string; items: Item[] }[] = [
  {
    name: "Write and review",
    items: [
      { href: "/check", label: "Check a post", hint: "Find problems before you publish", work: true },
      { href: "/review", label: "Review queue", hint: "Posts waiting for a decision", reviewers: true, work: true },
      { href: "/audit", label: "Audit log", hint: "Every decision, tamper-evident", work: true },
    ],
  },
  {
    name: "Brand rules",
    items: [
      { href: "/rules", label: "Rulebook", hint: "What the checker looks for", work: true },
      { href: "/facts", label: "Facts", hint: "Claims you can make, and their wording", work: true },
      { href: "/health", label: "Guideline health", hint: "Rules reviewers disagree with", work: true },
    ],
  },
  {
    name: "Proof",
    items: [
      { href: "/about", label: "How I know it works", hint: "Test results against a baseline" },
      { href: "/status", label: "Status", hint: "Is everything up right now?" },
    ],
  },
];

export type Profile = { display_name: string; role: string } | null;

const visible = (profile: Profile) => (i: Item) => (!i.work || profile) && (!i.reviewers || (profile && REVIEWERS.has(profile.role)));

/** Podium-style navigation: the mark on the left, the work in one line of bold uppercase on wide screens,
 * and a full-screen menu everywhere else. */
export function SiteNav({ profile }: { profile: Profile }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  const isActive = (href: string) => path === href || path.startsWith(href + "/");
  const bar = GROUPS.flatMap((g) => g.items).filter((i) => i.work && visible(profile)(i));

  // The menu is a sibling of the header: the header's backdrop blur would otherwise clip a fixed overlay.
  return (
    <>
    <header className="sticky top-0 z-40 border-b border-line bg-carbon/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between gap-6 px-4 sm:px-6">
        <Link href={profile ? "/check" : "/login"} className="flex shrink-0 items-center gap-2 text-bone">
          <Brandmark swing className="size-7" />
          <span className="font-display text-xl font-bold uppercase tracking-[-0.03em]">Plumbline</span>
        </Link>

        <nav aria-label="Main" className="hidden xl:block">
          <ul className="flex items-center gap-6">
            {bar.map(({ href, label, hint }) => (
              <li key={href}>
                <Link href={href} title={hint} aria-current={isActive(href) ? "page" : undefined}
                  className={`group relative block py-1 font-display text-[13px] font-bold uppercase tracking-[-0.02em] transition-colors ${isActive(href) ? "text-bone" : "text-bone/55 hover:text-bone"}`}>
                  {label}
                  {isActive(href) ? (
                    <motion.span layoutId="nav-active" aria-hidden className="absolute inset-x-0 -bottom-[18px] h-0.5 bg-iris" />
                  ) : (
                    <span aria-hidden className="absolute inset-x-0 -bottom-0.5 h-px origin-left scale-x-0 bg-bone transition-transform duration-300 group-hover:scale-x-100" />
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-4">
          {profile ? (
            <div className="hidden items-center gap-4 xl:flex">
              <div className="text-right font-label text-xs leading-tight uppercase">
                <p className="text-bone/55">Signed in as <span className="text-bone">{profile.display_name}</span></p>
                <p className="text-iris">{ROLE[profile.role] ?? profile.role}</p>
              </div>
              <SignOutButton />
            </div>
          ) : (
            <Link href="/login" className="hidden rounded-full bg-bone px-4 py-2 font-display text-xs font-bold uppercase text-carbon xl:block">Try it</Link>
          )}
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="site-menu"
            className="font-display text-lg font-bold uppercase tracking-[-0.03em] text-bone xl:hidden">
            {open ? "Close" : "Menu"}
          </button>
        </div>
      </div>
    </header>

      <AnimatePresence>
        {open && (
          <motion.div id="site-menu" data-lenis-prevent
            initial={{ clipPath: "inset(0 0 100% 0)" }} animate={{ clipPath: "inset(0 0 0% 0)" }} exit={{ clipPath: "inset(0 0 100% 0)" }}
            transition={{ duration: 0.6, ease: [0.76, 0, 0.24, 1] }}
            className="fixed inset-x-0 top-16 bottom-0 z-40 overflow-y-auto bg-carbon px-4 pt-8 pb-10 sm:px-6 xl:hidden">
            <div aria-hidden className="guides contours pointer-events-none absolute inset-0 opacity-60" />
            <nav aria-label="Main" className="relative mx-auto max-w-[1400px] space-y-8">
              {GROUPS.map((g) => {
                const items = g.items.filter(visible(profile));
                if (!items.length) return null;
                return (
                  <div key={g.name}>
                    <p className="font-label text-xs uppercase text-bone/45">{g.name}</p>
                    <ul className="mt-2">
                      {items.map(({ href, label, hint }, i) => (
                        <motion.li key={href} initial={{ y: 24, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                          transition={{ delay: 0.2 + i * 0.05, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}>
                          <Link href={href} aria-current={isActive(href) ? "page" : undefined}
                            className="group flex items-baseline justify-between gap-4 border-b border-line py-3">
                            <span className={`font-display text-3xl font-bold uppercase tracking-[-0.03em] transition-transform duration-300 group-hover:translate-x-2 sm:text-5xl ${isActive(href) ? "text-iris" : "text-bone"}`}>{label}</span>
                            <span className="hidden font-label text-xs uppercase text-bone/45 sm:block">{hint}</span>
                          </Link>
                        </motion.li>
                      ))}
                    </ul>
                  </div>
                );
              })}
              {profile ? (
                <div className="flex flex-wrap items-center justify-between gap-3 font-label text-sm uppercase">
                  <p className="text-bone/55">Signed in as <span className="text-bone">{profile.display_name}</span> · <span className="text-iris">{ROLE[profile.role] ?? profile.role}</span></p>
                  <SignOutButton />
                </div>
              ) : (
                <Link href="/login" className="inline-block rounded-full bg-bone px-5 py-2.5 font-display text-sm font-bold uppercase text-carbon">Sign in to try it</Link>
              )}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
