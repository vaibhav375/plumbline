"use client";

import { useFormStatus } from "react-dom";

import { Button } from "@/components/ui/button";

/** Disabled with "Signing in…" while the sign-in runs, so it can't be clicked twice. */
export function RoleButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} aria-label={`Try as ${label}`}
      className="h-11 w-full bg-white font-display text-sm font-bold uppercase tracking-wide text-ink hover:text-white">
      {pending ? "Signing in…" : `Try as ${label}`}
    </Button>
  );
}
