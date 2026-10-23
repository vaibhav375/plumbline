"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";

/** Shown when a page itself fails to render. Plain words; saved work lives on the server. */
export default function PageError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="mx-auto max-w-xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">This page didn&apos;t load properly</h1>
      <p>
        Anything you already checked or submitted is saved. Try loading the page again; if it keeps happening, the{" "}
        <Link href="/status" className="underline underline-offset-4">status page</Link> shows whether the checker is up.
      </p>
      {error.digest && <p className="text-xs text-muted-foreground">Reference: {error.digest}</p>}
      <div className="flex gap-3">
        <Button onClick={reset}>Try again</Button>
        <Button variant="outline" asChild><Link href="/check">Go to Check content</Link></Button>
      </div>
    </main>
  );
}
