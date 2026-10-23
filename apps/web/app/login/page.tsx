import Link from "next/link";

import { Button } from "@/components/ui/button";

import { signInAs, type DemoRole } from "./actions";

const ROLES: { role: DemoRole; label: string; who: string; can: string }[] = [
  { role: "creator", label: "Creator", who: "Asha, in-house writer", can: "Check a draft privately, accept cited fixes, and submit it for review." },
  { role: "agency", label: "Agency", who: "Sana, outside agency", can: "Check her own drafts; confidential facts stay hidden from her." },
  { role: "reviewer", label: "Reviewer", who: "Meera, content reviewer", can: "Work the review queue: uphold or overrule findings and approve." },
  { role: "compliance", label: "Compliance", who: "Arjun, compliance", can: "Decide claim and confidentiality findings, and give the compliance approval." },
  { role: "brand_owner", label: "Brand owner", who: "Kabir, brand owner", can: "Own the rulebook, import rules, and see which guidelines are unclear." },
];

const ERRORS: Record<string, string> = {
  signin: "Couldn't sign in to the demo account. Try again.",
  config: "Demo sign-in isn't configured on this deployment.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <main className="mx-auto max-w-5xl space-y-8 p-4 sm:p-6">
      <header className="space-y-3 pt-4">
        <p className="text-sm font-semibold tracking-wide text-accent-brand">PLUMBLINE</p>
        <h1 className="max-w-3xl text-3xl font-semibold leading-tight sm:text-4xl">
          Check marketing content against your brand&apos;s own rules and facts, before it&apos;s published.
        </h1>
        <p className="max-w-3xl">
          Every finding cites the rule or fact it comes from and the exact words; every check says what it didn&apos;t check.
          Pick a role to try it: each is a seeded demo account for Aurelle Skin, a fictional brand.
        </p>
        <p className="text-sm">
          <Link href="/about" className="underline underline-offset-4">How I know it works</Link>: the evaluation, its
          numbers with 95% intervals, and what leaves the system.
        </p>
      </header>
      {error && (
        <p role="alert" className="rounded-md border border-blocking px-4 py-3 text-sm text-blocking">
          {ERRORS[error] ?? ERRORS.signin}
        </p>
      )}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ROLES.map(({ role, label, who, can }) => (
          <li key={role} className="flex flex-col justify-between gap-3 rounded-lg border p-4">
            <div className="space-y-1">
              <h2 className="font-semibold">{label}</h2>
              <p className="text-xs text-muted-foreground">{who}</p>
              <p className="text-sm">{can}</p>
            </div>
            <form action={signInAs.bind(null, role)}>
              <Button type="submit" className="w-full">Try as {label}</Button>
            </form>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Demo runs on free model tiers using fictional data only; production uses paid no-training tiers or
        self-hosted Qwen.
      </p>
    </main>
  );
}
