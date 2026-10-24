"use client";

import { Link2 } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { WakingBanner } from "@/components/WakingBanner";
import { audit, type AuditVerify, CheckError } from "@/lib/api";

const when = (at: string) =>
  new Date(at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" });

export function AuditLog() {
  const [data, setData] = useState<AuditVerify | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const [exporting, setExporting] = useState(false);
  useEffect(() => {
    audit.verify(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load the audit log."));
  }, []);
  if (error) return <p role="alert" className="rounded-lg border border-blocking/40 bg-panel px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Verifying the chain…</p></>;

  return (
    <div className="space-y-6">
      {data.scope === "mine" ? (
        <section aria-labelledby="chain" className="rounded-2xl border border-line bg-panel p-5">
          <h2 id="chain" className="text-xl" data-testid="chain-status">
            Events about your work ({data.length})
          </h2>
          <p className="mt-1 text-sm">
            You see the decisions, approvals and status changes on your own content. Verifying the chain and exporting it
            need every event in the organisation, so reviewers, compliance, the brand owner and auditors do that.
          </p>
        </section>
      ) : (
        <section aria-labelledby="chain" className={`relative overflow-hidden rounded-2xl border p-5 ${data.valid ? "border-ok/40 bg-ok/[0.06]" : "border-blocking/40 bg-blocking/[0.06]"}`}>
          <div aria-hidden className="guides pointer-events-none absolute inset-0 opacity-50" />
          <h2 id="chain" className={`relative text-xl ${data.valid ? "text-ok" : "text-blocking"}`} data-testid="chain-status">
            {data.valid ? `Chain verified ✓ (${data.length} events)` : `Chain broken at event ${data.broken_at} of ${data.length}`}
          </h2>
          <Chain events={data.recent} length={data.length} brokenAt={data.broken_at} />
          <p className="relative mt-4 max-w-3xl text-sm text-bone/80">
            Each event stores a SHA-256 hash of the previous event&apos;s hash, its own content and its time. The checker just
            recomputed all {data.length}. Editing, removing or reordering any event breaks the chain from that point, and the
            database refuses updates and deletes to this log.
          </p>
          <div className="relative mt-4 flex flex-wrap items-center gap-3">
            <Button variant="outline" size="sm" disabled={exporting} onClick={async () => {
              setExporting(true);
              try {
                await audit.exportCsv();
              } catch (e) {
                setError(e instanceof CheckError ? e.message : "Couldn't export the audit log.");
              } finally {
                setExporting(false);
              }
            }}>
              {exporting ? "Exporting…" : "Export CSV"}
            </Button>
            <span className="text-xs text-ash">The export includes each event&apos;s exact payload, so anyone can recompute the hashes.</span>
          </div>
        </section>
      )}

      <section aria-labelledby="events" className="space-y-2">
        <h2 id="events" className="text-base">
          Newest events{data.recent.length < data.length ? ` (latest ${data.recent.length} of ${data.length}; export for all)` : ""}
        </h2>
        <div className="overflow-x-auto rounded-xl bg-panel ring-1 ring-line">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line font-label text-[11px] uppercase tracking-[0.14em] text-ash">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">When (IST)</th>
                <th scope="col" className="px-3 py-2 font-medium">Who</th>
                <th scope="col" className="px-3 py-2 font-medium">What</th>
                <th scope="col" className="px-3 py-2 font-medium">Reason</th>
                <th scope="col" className="px-3 py-2 font-medium">Hash</th>
              </tr>
            </thead>
            <tbody>
              {data.recent.map((e) => (
                <tr key={e.id} className="border-t border-line align-top transition-colors hover:bg-white/[0.03]">
                  <td className="whitespace-nowrap px-3 py-2">{when(e.at)}</td>
                  <td className="px-3 py-2">{e.who}</td>
                  <td className="min-w-48 px-3 py-2">{e.what}</td>
                  <td className="px-3 py-2 text-muted-foreground">{e.reason ?? ""}</td>
                  <td className="px-3 py-2 font-mono text-xs text-iris" title={e.hash}>{e.hash.slice(0, 12)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

/** The newest events as linked blocks, oldest on the left; each lights up as its hash is confirmed. */
function Chain({ events, length, brokenAt }: { events: AuditVerify["recent"]; length: number; brokenAt: number | null }) {
  const shown = events.slice(0, 5).reverse();
  return (
    <ol aria-label="The newest links in the chain" className="relative mt-5 flex items-stretch gap-0 overflow-x-auto pb-2">
      {shown.map((e, i) => {
        const index = length - (shown.length - 1 - i);
        const bad = brokenAt !== null && index >= brokenAt;
        return (
          <li key={e.id} className="flex shrink-0 items-center">
            {i > 0 && (
              <motion.span aria-hidden initial={{ opacity: 0.2 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 + i * 0.18 }}
                className={`flex items-center ${bad ? "text-blocking" : "text-ok"}`}>
                <span className="h-px w-5 bg-current" /><Link2 className="size-4" /><span className="h-px w-5 bg-current" />
              </motion.span>
            )}
            <motion.div initial={{ borderColor: "#2e2e34", y: 6, opacity: 0 }}
              animate={{ borderColor: bad ? "#ff6a5c" : "#3dc48a", y: 0, opacity: 1 }}
              transition={{ delay: 0.1 + i * 0.18, duration: 0.4 }}
              className="w-40 rounded-lg border-[1.5px] bg-carbon p-2.5" title={e.hash}>
              <p className="flex justify-between font-label text-[11px] font-semibold uppercase tracking-[0.12em] text-ash">
                <span>Event {index}</span><span className={bad ? "text-blocking" : "text-ok"}>{bad ? "broken" : "✓"}</span>
              </p>
              <p className="mt-1 truncate text-xs text-bone">{e.what}</p>
              <p className="mt-1 font-mono text-[11px] text-iris">{e.hash.slice(0, 14)}…</p>
            </motion.div>
          </li>
        );
      })}
    </ol>
  );
}
