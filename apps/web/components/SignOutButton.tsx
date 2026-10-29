"use client";

import { useFormStatus } from "react-dom";

import { signOut } from "@/app/login/actions";

function Inner({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} className="rounded-full border border-bone/30 px-3.5 py-1.5 font-display text-xs font-bold uppercase tracking-[-0.01em] text-bone transition-colors hover:border-bone hover:bg-bone hover:text-carbon disabled:opacity-60">
      {pending ? "Signing out…" : label}
    </button>
  );
}

/** Signing out is also how a visitor switches demo role: the role picker is the login page. */
export function SignOutButton({ label = "Sign out" }: { label?: string }) {
  return <form action={signOut}><Inner label={label} /></form>;
}
