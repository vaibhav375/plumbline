"use client";

import { useFormStatus } from "react-dom";

import { signOut } from "@/app/login/actions";

function Inner() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} className="text-sm font-medium text-white/80 underline-offset-4 hover:text-white hover:underline disabled:opacity-60">
      {pending ? "Signing out…" : "Sign out"}
    </button>
  );
}

export function SignOutButton() {
  return <form action={signOut}><Inner /></form>;
}
