"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type QueueRow, review } from "@/lib/api";

const STATUS: Record<string, string> = {
  submitted: "Submitted",
  in_review: "In review",
  changes_requested: "Changes requested",
  approved: "Approved",
};

export function Queue() {
  const [rows, setRows] = useState<QueueRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  useEffect(() => {
    review.queue(setWaking).then(setRows, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load the queue."));
  }, []);
  if (error) return <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">{error}</p>;
  if (!rows) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;
  if (!rows.length) return <p>Nothing is waiting for review.</p>;
  return (
    <ul className="space-y-3">
      {rows.map((r) => (
        <li key={r.version_id}>
          <Link href={`/review/${r.version_id}`} className="block rounded-lg border p-4 hover:bg-muted/40">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-medium">{r.title ?? "Untitled"}</span>
              <span className="text-sm">{STATUS[r.status] ?? r.status}</span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {r.author} · {r.origin} · {r.channel} · version {r.n}
            </p>
            <p className="mt-2 text-sm">
              <strong>{r.blocking} blocking</strong> · {r.claims} claim or confidential ·{" "}
              {r.pending.length ? `Waiting for: ${r.pending.join(", ")}` : "All approvals in"}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
