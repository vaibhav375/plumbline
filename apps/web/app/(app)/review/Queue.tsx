"use client";

import { ArrowUpRight } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { StagePipeline } from "@/components/StagePipeline";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type QueueRow, review } from "@/lib/api";

const STATUS: Record<string, string> = {
  submitted: "Submitted",
  in_review: "In review",
  changes_requested: "Changes requested",
  approved: "Approved",
};
const STATUS_TONE: Record<string, string> = {
  submitted: "border-iris/60 text-iris",
  in_review: "border-major/60 text-major",
  changes_requested: "border-blocking/60 text-blocking",
  approved: "border-ok/60 text-ok",
};

export function Queue() {
  const [rows, setRows] = useState<QueueRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  useEffect(() => {
    review.queue(setWaking).then(setRows, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load the queue."));
  }, []);
  if (error) return <p role="alert" className="rounded-xl border border-blocking/40 bg-blocking/[0.07] px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!rows) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;
  if (!rows.length) return <p>Nothing is waiting for review.</p>;
  const maxBlocking = Math.max(1, ...rows.map((r) => r.blocking));
  const stats: [string, number, string][] = [
    ["Waiting", rows.filter((r) => r.status !== "approved").length, "text-bone"],
    ["Blocking, still waiting", rows.filter((r) => r.status !== "approved").reduce((a, r) => a + r.blocking, 0), "text-blocking"],
    ["Need compliance", rows.filter((r) => r.status !== "approved" && r.pending.includes("compliance")).length, "text-iris"],
    ["Approved", rows.filter((r) => r.status === "approved").length, "text-ok"],
  ];
  return (
    <div className="space-y-6">
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Queue summary">
        {stats.map(([label, n, c]) => (
          <li key={label} className="rounded-xl border border-line bg-panel p-4">
            <p className={`font-display text-4xl font-bold tabular-nums ${c}`}>{n}</p>
            <p className="font-label text-[11px] font-semibold uppercase text-ash">{label}</p>
          </li>
        ))}
      </ul>
      <ul className="space-y-3">
        {rows.map((r, i) => (
          <motion.li key={r.version_id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i, 12) * 0.04, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}>
            <Link href={`/review/${r.version_id}`}
              className="group grid gap-4 rounded-xl border border-line bg-panel p-4 transition-colors duration-300 hover:border-bone/40 hover:bg-raised sm:grid-cols-[6.5rem_minmax(0,1fr)_auto] sm:items-center">
              {/* Risk: the blocking count, with a bar scaled to the riskiest post in the queue. */}
              <div className="flex items-center gap-3 sm:block">
                <p className={`font-display text-4xl leading-none font-bold tabular-nums ${r.blocking ? "text-blocking" : "text-ok"}`}>{r.blocking}</p>
                <div>
                  <p className="font-label text-[11px] font-semibold uppercase text-ash sm:mt-1">blocking</p>
                  <div aria-hidden className="mt-1 h-1.5 w-20 rounded-full bg-raised">
                    <div className="h-1.5 rounded-full bg-blocking" style={{ width: `${(r.blocking / maxBlocking) * 100}%` }} />
                  </div>
                </div>
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-lg font-semibold text-bone">{r.title ?? "Untitled"}</span>
                  <span className={`rounded border px-2 py-0.5 font-label text-[11px] font-semibold uppercase ${STATUS_TONE[r.status] ?? "border-line text-ash"}`}>
                    {STATUS[r.status] ?? r.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-ash">
                  {r.author} · {r.origin} · {r.channel} · version {r.n} · {r.claims} claim or confidential
                </p>
                <div className="mt-3 overflow-x-auto">
                  <StagePipeline required={r.required} approved={r.approved} compact />
                </div>
                <p className="sr-only">{r.pending.length ? `Waiting for: ${r.pending.join(", ")}` : "All approvals in"}</p>
              </div>
              <span aria-hidden className="hidden size-10 items-center justify-center rounded-full border border-line text-bone transition-all duration-300 group-hover:border-bone group-hover:bg-bone group-hover:text-carbon sm:inline-flex">
                <ArrowUpRight className="size-5 transition-transform duration-300 group-hover:rotate-45" />
              </span>
            </Link>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
