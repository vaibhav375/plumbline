import { Button } from "@/components/ui/button";

import { signInAs, type DemoRole } from "./actions";

const ROLES: { role: DemoRole; label: string; who: string }[] = [
  { role: "creator", label: "Creator", who: "Asha writes posts for the brand." },
  { role: "agency", label: "Agency", who: "Sana is an outside agency writer; confidential details stay hidden." },
  { role: "reviewer", label: "Reviewer", who: "Meera reviews submitted content." },
  { role: "compliance", label: "Compliance", who: "Arjun decides claims and confidential findings." },
  { role: "brand_owner", label: "Brand owner", who: "Kabir owns the rulebook and guideline health." },
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
    <main className="mx-auto max-w-xl space-y-6 p-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">Plumbline</h1>
        <p>Checks brand content against your rulebook and fact ledger, cites every finding, and says what it didn&apos;t check.</p>
      </header>
      {error && (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">
          {ERRORS[error] ?? ERRORS.signin}
        </p>
      )}
      <ul className="space-y-3">
        {ROLES.map(({ role, label, who }) => (
          <li key={role} className="flex items-center justify-between gap-4 rounded-lg border p-4">
            <p className="text-sm">{who}</p>
            <form action={signInAs.bind(null, role)}>
              <Button type="submit">Try as {label}</Button>
            </form>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Demo runs on free model tiers using fictional data only; production uses paid no-training tiers or
        self-hosted Qwen. Aurelle Skin is a fictional brand.
      </p>
    </main>
  );
}
