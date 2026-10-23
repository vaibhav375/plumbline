"use client";

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
  if (error) return <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Verifying the chain…</p></>;

  return (
    <div className="space-y-6">
      <section aria-labelledby="chain" className={`rounded-lg border p-4 ${data.valid ? "border-green-300 bg-green-50 text-green-950" : "border-red-300 bg-red-50 text-red-950"}`}>
        <h2 id="chain" className="text-lg font-semibold" data-testid="chain-status">
          {data.valid ? `Chain verified ✓ (${data.length} events)` : `Chain broken at event ${data.broken_at} of ${data.length}`}
        </h2>
        <p className="mt-1 text-sm">
          Each event stores a SHA-256 hash of the previous event&apos;s hash, its own content and its time. The checker just
          recomputed all {data.length}. Editing, removing or reordering any event breaks the chain from that point, and the
          database refuses updates and deletes to this log.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
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
          <span className="text-xs">The export includes each event&apos;s exact payload, so anyone can recompute the hashes.</span>
        </div>
      </section>

      <section aria-labelledby="events" className="space-y-2">
        <h2 id="events" className="font-semibold">
          Newest events{data.recent.length < data.length ? ` (latest ${data.recent.length} of ${data.length}; export for all)` : ""}
        </h2>
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50">
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
                <tr key={e.id} className="border-t align-top">
                  <td className="whitespace-nowrap px-3 py-2">{when(e.at)}</td>
                  <td className="px-3 py-2">{e.who}</td>
                  <td className="px-3 py-2">{e.what}</td>
                  <td className="px-3 py-2 text-muted-foreground">{e.reason ?? ""}</td>
                  <td className="px-3 py-2 font-mono text-xs" title={e.hash}>{e.hash.slice(0, 12)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
