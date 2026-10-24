"use client";

import { useFormStatus } from "react-dom";

import { Button } from "@/components/ui/button";

/** Disabled with "Signing in…" while the sign-in runs, so it can't be clicked twice. */
export function RoleButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} aria-label={`Try as ${label}`}
      className="h-auto min-h-11 w-full whitespace-normal py-2 font-display text-xs font-bold uppercase leading-tight tracking-wide">
      {pending ? "Signing in…" : `Try as ${label}`}
    </Button>
  );
}
