import { ArrowRight, BadgeCheck, Building2, ClipboardCheck, Megaphone, PenLine } from "lucide-react";
import Link from "next/link";

import { Brandmark } from "@/components/Brandmark";

import { signInAs, type DemoRole } from "./actions";
import { RoleButton } from "./RoleButton";

const ROLES: { role: DemoRole; label: string; who: string; can: string; lands: string; icon: typeof PenLine }[] = [
  { role: "creator", label: "Creator", who: "Asha, in-house writer", can: "Check a draft privately, accept cited fixes and send it for review.", lands: "Check a post", icon: PenLine },
  { role: "agency", label: "Agency", who: "Sana, outside agency", can: "Check her own drafts. Confidential facts stay hidden from her.", lands: "Check a post", icon: Building2 },
  { role: "reviewer", label: "Reviewer", who: "Meera, content reviewer", can: "Work through the queue: uphold or overrule findings, then approve.", lands: "Review queue", icon: BadgeCheck },
  { role: "compliance", label: "Compliance", who: "Arjun, compliance", can: "Decide claims and confidential findings, and give the compliance sign-off.", lands: "Review queue", icon: ClipboardCheck },
  { role: "brand_owner", label: "Brand owner", who: "Kabir, brand owner", can: "Own the rulebook and see which rules people find unclear.", lands: "Guideline health", icon: Megaphone },
];

const ERRORS: Record<string, string> = {
  signin: "Couldn't sign in to the demo account. Try again.",
  config: "Demo sign-in isn't configured on this deployment.",
};

/** What a check looks like, using a real line from the sample post. */
function Example() {
  return (
    <figure className="rise-in rounded-2xl bg-white p-5 text-ink shadow-[0_20px_50px_-24px_rgba(20,27,45,0.35)] ring-1 ring-ink/5">
      <p className="text-[15px] leading-relaxed">
        Meet the new Aurelle Vitamin C serum, now{" "}
        <mark className="rounded bg-blocking/10 px-0.5 text-ink ring-1 ring-blocking/60">clinically proven to fade dark spots by 60% in just 2 weeks</mark>.
      </p>
      <div className="mt-4 space-y-3 border-l-2 border-accent-brand pl-4">
        <p className="text-sm">
          <span className="mr-2 rounded border border-blocking px-1.5 py-0.5 text-xs font-semibold text-blocking">Blocking</span>
          The evidence says <b>32% in 8 weeks</b>, not 60% in 2.
        </p>
        <p className="font-mono text-xs text-muted-foreground">Cites FACT-014 · in-house study, 48 participants</p>
        <p className="rounded-lg bg-ok/5 p-3 text-sm ring-1 ring-ok/30">
          <span className="font-medium text-ok">Approved wording:</span> shown to visibly reduce dark spots by 32% in 8 weeks*
        </p>
      </div>
      <figcaption className="mt-4 text-xs text-muted-foreground">Every finding names its rule or fact and quotes the exact words.</figcaption>
    </figure>
  );
}

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <div className="min-h-dvh">
      <div className="bg-ink text-white">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:py-16">
          <header className="space-y-5">
            <div className="flex items-center gap-3">
              <Brandmark swing className="size-10 text-white/80" />
              <span className="font-display text-xl font-bold tracking-tight">Plumbline</span>
            </div>
            <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl">
              Check marketing content against your brand&apos;s own rules and facts, before it&apos;s published.
            </h1>
            <p className="max-w-xl text-lg text-white/75">
              Paste a post and see what breaks your rules, which claims your evidence doesn&apos;t back, and the approved way to say
              it. Plumbline also tells you what it didn&apos;t check, so nothing is quietly waved through.
            </p>
            <Link href="/about" className="inline-flex items-center gap-1.5 text-sm font-medium text-[#C9C4FA] hover:text-white">
              How I know it works: tested against a baseline <ArrowRight className="size-4" aria-hidden />
            </Link>
          </header>
          <Example />
        </div>
      </div>

      <main className="mx-auto max-w-6xl space-y-5 px-4 py-10 sm:px-6">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight">Try it as one of the team</h2>
          <p className="text-muted-foreground">
            Five demo accounts for Aurelle Skin, a fictional brand. No sign-up; each role opens where its work is.
          </p>
        </div>
        {error && (
          <p role="alert" className="rounded-md border border-blocking bg-white px-4 py-3 text-sm text-blocking">
            {ERRORS[error] ?? ERRORS.signin}
          </p>
        )}
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {ROLES.map(({ role, label, who, can, lands, icon: Icon }) => (
            <li key={role} className="flex flex-col justify-between gap-4 rounded-xl bg-white p-4 shadow-sm ring-1 ring-ink/5 transition-shadow hover:shadow-md">
              <div className="space-y-2">
                <span className="inline-flex size-9 items-center justify-center rounded-lg bg-accent-brand/10 text-accent-brand">
                  <Icon className="size-5" aria-hidden />
                </span>
                <h3 className="font-display text-lg font-bold">{label}</h3>
                <p className="text-xs text-muted-foreground">{who}</p>
                <p className="text-sm">{can}</p>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Opens: {lands}</p>
                <form action={signInAs.bind(null, role)}>
                  <RoleButton label={label} />
                </form>
              </div>
            </li>
          ))}
        </ul>
        <p className="text-xs text-muted-foreground">
          Demo runs on free model tiers using fictional data only; production uses paid no-training tiers or self-hosted Qwen.
        </p>
      </main>
      <footer className="mx-auto flex max-w-6xl flex-wrap gap-x-4 gap-y-1 px-4 pb-8 text-sm text-muted-foreground sm:px-6">
        <Link href="/status" className="underline-offset-4 hover:underline">Status</Link>
        <Link href="/about" className="underline-offset-4 hover:underline">How I know it works</Link>
        <span>Aurelle Skin is a fictional brand; no real data is used.</span>
      </footer>
    </div>
  );
}
