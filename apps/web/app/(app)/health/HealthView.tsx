"use client";

import { useEffect, useState } from "react";

import { IntervalChart, wilson } from "@/components/charts/IntervalChart";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, guidelineHealth, type HealthResponse, type HealthRow } from "@/lib/api";

const pct = (x: number | null) => (x === null ? "–" : `${Math.round(x * 100)}%`);
const ORIGIN: Record<string, string> = { employee: "Employees", agency: "Agencies", ai_tool: "AI tool users", freelancer: "Freelancers" };

function status(r: HealthRow, min: number) {
  switch (r.status) {
    case "ready":
      return { label: "Ready to block", tone: "border-ok/50 bg-ok/10 text-ok" };
    case "blocks":
      return { label: r.tier === "mandatory" ? "Blocks (mandatory)" : "Blocks (graduated)", tone: "border-line bg-raised text-bone" };
    case "too_few":
      return { label: `Too few decisions (n < ${min})`, tone: "border-line text-ash" };
    default:
      return { label: "Still advisory", tone: "border-line text-bone" };
  }
}

export function HealthView() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  useEffect(() => {
    guidelineHealth(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load guideline health."));
  }, []);
  if (error) return <p role="alert" className="rounded-lg border border-blocking/40 bg-panel px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;

  return (
    <div className="space-y-6">
      {data.synthetic && (
        <p role="note" className="rounded-xl border border-major/50 bg-major/[0.07] px-4 py-3 text-sm text-major">
          <strong>Includes synthetic demo history:</strong> generated reviewer decisions, not real data, so the page has something to show.
        </p>
      )}
      <section aria-labelledby="hero" className="space-y-2">
        <h2 id="hero" className={`text-3xl leading-[0.95] sm:text-4xl ${data.unclear ? "text-major" : "text-ok"}`} data-testid="unclear-count">
          {data.unclear === 0
            ? "No rule looks unclear yet"
            : `${data.unclear} ${data.unclear === 1 ? "rule may be unclear: reviewers overruled it" : "rules may be unclear: reviewers overruled them"} often`}
        </h2>
        <p className="max-w-4xl text-sm text-ash">
          {data.scope === "mine" ? "Your submitted drafts only. " : "All submitted content. "}
          Private pre-checks never count. Accepted fixes and upholds count as agreeing; overrules and dismissals as disagreeing.
          The lower bound is a 95% Wilson bound: we are 95% sure agreement is at least that high. A brand rule is ready to block
          once its lower bound reaches 80%; a rule may be unclear once we are 95% sure reviewers disagree at least a quarter of
          the time. Under {data.min_decisions} decisions is too few to say either.
        </p>
      </section>

      {data.rules.some((r) => r.decisions > 0) && (
        <section aria-labelledby="agreement" className="relative overflow-hidden rounded-2xl bg-panel p-5 ring-1 ring-line">
          <h2 id="agreement" className="text-lg">How often reviewers agree with each rule</h2>
          <p className="mb-2 text-sm text-muted-foreground">
            Dot: share of decisions that agreed. Line: the range we are 95% sure it lies in. A brand rule is ready to block
            once the whole range is right of the plumb line.
          </p>
          <IntervalChart
            series={[{ name: "Agreement", color: "#8A80F2" }]}
            threshold={{ value: 0.8, label: "Ready to block · 80%" }}
            caption="Rules with at least one decision. The table below has the same numbers."
            rows={data.rules
              .filter((r) => r.decisions > 0)
              .map((r) => {
                const [lo, hi] = wilson(r.upheld, r.decisions);
                return {
                  label: r.rule_id,
                  sub: r.title ?? undefined,
                  points: [{
                    value: r.agreement ?? 0,
                    lo,
                    hi,
                    label: pct(r.agreement),
                    tip: `${r.rule_id}: ${r.upheld} of ${r.decisions} decisions agreed (${pct(r.agreement)}); 95% range ${pct(lo)}–${pct(hi)}`,
                  }],
                };
              })}
          />
        </section>
      )}

      {data.rules.length === 0 ? (
        <p>No rule has flagged {data.scope === "mine" ? "your submitted drafts" : "submitted content"} yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl bg-panel ring-1 ring-line">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line font-label text-[11px] uppercase text-ash">
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
                        <span className="mt-1 inline-block rounded border border-major/50 bg-major/10 px-2 py-0.5 font-label text-[11px] font-semibold uppercase text-major">
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
          <h2 id="origin" className="text-lg">By origin</h2>
          <p className="text-sm text-muted-foreground">Groups of fewer than 3 people are hidden, and there are no individual rankings.</p>
          {data.by_origin.length === 0 ? (
            <p className="text-sm">No group is large enough to show yet.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl bg-panel ring-1 ring-line">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line font-label text-[11px] uppercase text-ash">
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
                      <td className="px-3 py-2 tabular-nums">
                        <span className="flex items-center gap-2">
                          {(o.blocking / Math.max(o.versions, 1)).toFixed(1)}
                          <span aria-hidden className="h-1.5 w-24 rounded-full bg-raised">
                            <span className="block h-1.5 rounded-full bg-blocking"
                              style={{ width: `${(o.blocking / Math.max(o.versions, 1) / Math.max(...data.by_origin!.map((x) => x.blocking / Math.max(x.versions, 1)), 0.1)) * 100}%` }} />
                          </span>
                        </span>
                      </td>
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
