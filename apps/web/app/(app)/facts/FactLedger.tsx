"use client";

import { useEffect, useState } from "react";

import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type FactRow, type FactsResponse, rulebook } from "@/lib/api";

const CONF: Record<FactRow["confidentiality"], string> = {
  public: "border-slate-300 bg-slate-50 text-slate-900",
  internal: "border-sky-300 bg-sky-50 text-sky-950",
  confidential: "border-purple-300 bg-purple-50 text-purple-950",
  embargoed: "border-purple-300 bg-purple-50 text-purple-950",
};
const chip = "rounded border px-2 py-0.5 text-xs font-medium";

function Fact({ f }: { f: FactRow }) {
  return (
    <article aria-label={f.id} className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs">{f.id}</span>
        <span className={`${chip} ${CONF[f.confidentiality]}`}>
          {f.confidentiality}
          {f.confidentiality === "embargoed" && f.embargo_until ? ` until ${f.embargo_until}` : ""}
        </span>
        {!f.verified && <span className={`${chip} border-amber-300 bg-amber-50 text-amber-950`}>Unverified</span>}
        {f.expired && <span className={`${chip} border-red-300 bg-red-50 text-red-900`}>Expired</span>}
      </div>
      <p className="mt-2 font-medium">{f.statement}</p>
      <p className={`mt-1 text-xs ${f.expired ? "text-red-800" : "text-muted-foreground"}`}>
        {[f.product, f.market, `owner: ${f.owner}`].filter(Boolean).join(" · ")} · valid from {f.valid_from}
        {f.valid_until ? ` until ${f.valid_until}` : ", no end date"}
      </p>
      {f.wordings.length > 0 && (
        <ul aria-label={`Approved wordings for ${f.id}`} className="mt-3 space-y-2 border-l-2 pl-3 text-sm">
          {f.wordings.map((w) => (
            <li key={w.id}>
              <span className="font-mono text-xs">{w.id}</span> <span className="text-xs text-muted-foreground">({w.channel}, {w.market})</span>
              <p>“{w.text}”</p>
              {w.disclaimer && <p className="text-xs text-muted-foreground">Must carry: {w.disclaimer}</p>}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

export function FactLedger() {
  const [data, setData] = useState<FactsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  useEffect(() => {
    rulebook.facts(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load the fact ledger."));
  }, []);
  if (error) return <p role="alert" className="rounded-lg border border-blocking/40 bg-white px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;
  const expired = data.facts.filter((f) => f.expired).length;
  const unverified = data.facts.filter((f) => !f.verified).length;

  return (
    <div className="space-y-4">
      {data.restricted && (
        <p role="note" className="rounded-md border px-4 py-3 text-sm">
          Some facts are restricted. Confidential and embargoed facts are visible only to reviewers, compliance and the brand
          owner; the checker still checks your drafts against them.
        </p>
      )}
      <p className="text-sm">
        {data.facts.length} facts · {expired} expired · {unverified} unverified · dates are checked against {data.today} (India time).
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {data.facts.map((f) => <Fact key={f.id} f={f} />)}
      </div>
    </div>
  );
}
