"use client";

import { useFormStatus } from "react-dom";

import { Button } from "@/components/ui/button";

/** Disabled with "Signing in…" while the sign-in runs, so it can't be clicked twice. */
export function RoleButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} className="w-full" aria-label={`Try as ${label}`}>
      {pending ? "Signing in…" : `Try as ${label}`}
    </Button>
  );
}
