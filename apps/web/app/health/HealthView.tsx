"use client";

import { useEffect, useState } from "react";

import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, guidelineHealth, type HealthResponse, type HealthRow } from "@/lib/api";

const pct = (x: number | null) => (x === null ? "–" : `${Math.round(x * 100)}%`);
const ORIGIN: Record<string, string> = { employee: "Employees", agency: "Agencies", ai_tool: "AI tool users", freelancer: "Freelancers" };

function status(r: HealthRow, min: number) {
  switch (r.status) {
    case "ready":
      return { label: "Ready to block", tone: "border-green-300 bg-green-50 text-green-950" };
    case "blocks":
      return { label: r.tier === "mandatory" ? "Blocks (mandatory)" : "Blocks (graduated)", tone: "border-slate-300 bg-slate-50 text-slate-900" };
    case "too_few":
      return { label: `Too few decisions (n < ${min})`, tone: "border-slate-300 bg-white text-slate-700" };
    default:
      return { label: "Still advisory", tone: "border-slate-300 bg-white text-slate-900" };
  }
}

export function HealthView() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  useEffect(() => {
    guidelineHealth(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load guideline health."));
  }, []);
  if (error) return <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;

  return (
    <div className="space-y-6">
      {data.synthetic && (
        <p role="note" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <strong>Includes synthetic demo history:</strong> generated reviewer decisions, not real data, so the page has something to show.
        </p>
      )}
      <section aria-labelledby="hero" className="space-y-2">
        <h2 id="hero" className="text-xl font-semibold" data-testid="unclear-count">
          {data.unclear === 0
            ? "No rule looks unclear yet"
            : `${data.unclear} ${data.unclear === 1 ? "rule may be unclear: reviewers overruled it" : "rules may be unclear: reviewers overruled them"} often`}
        </h2>
        <p className="text-sm text-muted-foreground">
          {data.scope === "mine" ? "Your submitted drafts only. " : "All submitted content. "}
          Private pre-checks never count. Accepted fixes and upholds count as agreeing; overrules and dismissals as disagreeing.
          The lower bound is a 95% Wilson bound: we are 95% sure agreement is at least that high. A brand rule is ready to block
          once its lower bound reaches 80%; a rule may be unclear once we are 95% sure reviewers disagree at least a quarter of
          the time. Under {data.min_decisions} decisions is too few to say either.
        </p>
      </section>

      {data.rules.length === 0 ? (
        <p>No rule has flagged {data.scope === "mine" ? "your submitted drafts" : "submitted content"} yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50">
              <tr>
                {["Rule", "Flags", "Upheld", "Overruled", "Dismissed", "Agreement", "Lower bound", "Status"].map((h) => (
                  <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rules.map((r) => {
                const s = status(r, data.min_decisions);
                return (
                  <tr key={r.rule_id} className="border-t align-top" data-rule={r.rule_id}>
                    <td className="min-w-56 px-3 py-2">
                      <span className="font-mono text-xs">{r.rule_id}</span>
                      {r.title && <p>{r.title}</p>}
                      {r.unclear && (
                        <span className="mt-1 inline-block rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs text-amber-950">
                          May be unclear
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 tabular-nums">{r.flags}</td>
                    <td className="px-3 py-2 tabular-nums">{r.upheld}</td>
                    <td className="px-3 py-2 tabular-nums">{r.overruled}</td>
                    <td className="px-3 py-2 tabular-nums">{r.dismissed}</td>
                    <td className="px-3 py-2 tabular-nums">{pct(r.agreement)}</td>
                    <td className="px-3 py-2 tabular-nums">{pct(r.wilson_lower)}</td>
                    <td className="px-3 py-2">
                      <span className={`whitespace-nowrap rounded border px-2 py-0.5 text-xs font-medium ${s.tone}`}>{s.label}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {data.by_origin && (
        <section aria-labelledby="origin" className="space-y-2">
          <h2 id="origin" className="font-semibold">By origin</h2>
          <p className="text-sm text-muted-foreground">Groups of fewer than 3 people are hidden, and there are no individual rankings.</p>
          {data.by_origin.length === 0 ? (
            <p className="text-sm">No group is large enough to show yet.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    {["Origin", "People", "Versions", "Findings per version", "Blocking per version"].map((h) => (
                      <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.by_origin.map((o) => (
                    <tr key={o.origin} className="border-t">
                      <td className="px-3 py-2">{ORIGIN[o.origin] ?? o.origin}</td>
                      <td className="px-3 py-2 tabular-nums">{o.authors}</td>
                      <td className="px-3 py-2 tabular-nums">{o.versions}</td>
                      <td className="px-3 py-2 tabular-nums">{(o.findings / Math.max(o.versions, 1)).toFixed(1)}</td>
                      <td className="px-3 py-2 tabular-nums">{(o.blocking / Math.max(o.versions, 1)).toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
