"use client";

import { useFormStatus } from "react-dom";

import { signOut } from "@/app/login/actions";

function Inner() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} className="rounded-full border border-bone/30 px-3.5 py-1.5 font-display text-xs font-bold uppercase tracking-[-0.01em] text-bone transition-colors hover:border-bone hover:bg-bone hover:text-carbon disabled:opacity-60">
      {pending ? "Signing out…" : "Sign out"}
    </button>
  );
}

export function SignOutButton() {
  return <form action={signOut}><Inner /></form>;
}
