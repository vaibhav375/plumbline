"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";

import { Packshot } from "@/components/Packshot";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type FactRow, type FactsResponse, rulebook } from "@/lib/api";

const CONF: Record<FactRow["confidentiality"], string> = {
  public: "border-line bg-raised text-bone",
  internal: "border-minor/50 bg-minor/10 text-minor",
  confidential: "border-iris/50 bg-iris/10 text-iris",
  embargoed: "border-iris/50 bg-iris/10 text-iris",
};
const chip = "rounded border px-2 py-0.5 font-label text-[11px] font-semibold uppercase tracking-[0.12em]";
const day = (d: string) => new Date(`${d}T00:00:00Z`).getTime();
const fmt = (d: string) => new Date(`${d}T00:00:00Z`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

function Fact({ f }: { f: FactRow }) {
  return (
    <article aria-label={f.id} className={`flex gap-4 rounded-xl bg-panel p-4 ring-1 transition-colors hover:ring-bone/30 ${f.expired ? "ring-blocking/40" : "ring-line"}`}>
      <Packshot product={f.product} className="h-20 w-14 shrink-0" />
      <div className="min-w-0 grow">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-ash">{f.id}</span>
        <span className={`${chip} ${CONF[f.confidentiality]}`}>
          {f.confidentiality}
          {f.confidentiality === "embargoed" && f.embargo_until ? ` until ${f.embargo_until}` : ""}
        </span>
        {!f.verified && <span className={`${chip} border-major/50 bg-major/10 text-major`}>Unverified</span>}
        {f.expired && <span className={`${chip} border-blocking/50 bg-blocking/10 text-blocking`}>Expired</span>}
      </div>
      <p className="mt-2 font-medium leading-snug text-bone">{f.statement}</p>
      <p className={`mt-1 text-xs ${f.expired ? "text-blocking" : "text-muted-foreground"}`}>
        {[f.product, f.market, `owner: ${f.owner}`].filter(Boolean).join(" · ")} · valid from {f.valid_from}
        {f.valid_until ? ` until ${f.valid_until}` : ", no end date"}
      </p>
      {f.wordings.length > 0 && (
        <ul aria-label={`Approved wordings for ${f.id}`} className="mt-3 space-y-2 border-l-2 border-iris/50 pl-3 text-sm">
          {f.wordings.map((w) => (
            <li key={w.id}>
              <span className="font-mono text-xs">{w.id}</span> <span className="text-xs text-muted-foreground">({w.channel}, {w.market})</span>
              <p>“{w.text}”</p>
              {w.disclaimer && <p className="text-xs text-muted-foreground">Must carry: {w.disclaimer}</p>}
            </li>
          ))}
        </ul>
      )}
      </div>
    </article>
  );
}

export function FactLedger() {
  const [data, setData] = useState<FactsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const [product, setProduct] = useState<string | null>(null);
  useEffect(() => {
    rulebook.facts(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load the fact ledger."));
  }, []);
  if (error) return <p role="alert" className="rounded-lg border border-blocking/40 bg-panel px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;
  const expired = data.facts.filter((f) => f.expired).length;
  const unverified = data.facts.filter((f) => !f.verified).length;

  const products = [...new Set(data.facts.map((f) => f.product ?? "Brand-wide"))];
  const shown = data.facts.filter((f) => !product || (f.product ?? "Brand-wide") === product);

  return (
    <div className="space-y-8">
      {data.restricted && (
        <p role="note" className="rounded-xl border border-iris/40 bg-iris/[0.07] px-4 py-3 text-sm">
          Some facts are restricted. Confidential and embargoed facts are visible only to reviewers, compliance and the brand
          owner; the checker still checks your drafts against them.
        </p>
      )}
      <ul className="grid grid-cols-3 gap-3 sm:grid-cols-5" aria-label="Fact counts">
        {[["Facts", data.facts.length, "text-bone"], ["Expired", expired, "text-blocking"], ["Unverified", unverified, "text-major"],
          ["With an end date", data.facts.filter((f) => f.valid_until).length, "text-bone"], ["Approved wordings", data.facts.reduce((a, f) => a + f.wordings.length, 0), "text-iris"]]
          .map(([label, n, c]) => (
            <li key={label as string} className="rounded-xl border border-line bg-panel p-3">
              <p className={`font-display text-3xl font-extrabold tabular-nums ${c}`}>{n}</p>
              <p className="font-label text-[11px] font-semibold uppercase tracking-[0.14em] text-ash">{label}</p>
            </li>
          ))}
      </ul>
      <p className="text-sm text-ash">Dates are checked against {fmt(data.today)} (India time).</p>

      <Timeline facts={data.facts} today={data.today} />

      <section aria-labelledby="shelf" className="space-y-3">
        <h2 id="shelf" className="text-base">The shelf</h2>
        <div className="flex gap-2 overflow-x-auto pb-2" role="group" aria-label="Show facts for">
          {[null, ...products].map((p) => {
            const on = product === p;
            return (
              <button key={p ?? "all"} type="button" aria-pressed={on} onClick={() => setProduct(p)}
                className={`group flex w-28 shrink-0 flex-col items-center gap-1 rounded-xl border px-2 pt-3 pb-2 text-center transition-colors ${on ? "border-bone/60 bg-raised" : "border-line bg-panel hover:border-bone/30"}`}>
                {p ? <Packshot product={p === "Brand-wide" ? null : p} className="h-16 w-11 transition-transform duration-500 ease-out group-hover:-translate-y-1" />
                  : <span className="flex h-16 items-center font-display text-2xl font-extrabold">All</span>}
                <span className="line-clamp-2 text-[11px] leading-tight text-bone/80">{p ?? `${data.facts.length} facts`}</span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="grid gap-3 md:grid-cols-2">
        {shown.map((f) => <Fact key={f.id} f={f} />)}
      </div>
    </div>
  );
}

/** Facts with an end date, on one time axis, with today marked: what is about to expire is visible at a glance. */
function Timeline({ facts, today }: { facts: FactRow[]; today: string }) {
  const dated = facts.filter((f) => f.valid_until).sort((a, b) => day(a.valid_until!) - day(b.valid_until!));
  if (!dated.length) return null;
  const t0 = Math.min(...dated.map((f) => day(f.valid_from)), day(today));
  const t1 = Math.max(...dated.map((f) => day(f.valid_until!)), day(today)) + 30 * 864e5;
  const pos = (d: string) => ((day(d) - t0) / (t1 - t0)) * 100;
  const x = (d: string) => `${pos(d)}%`;
  return (
    <section aria-labelledby="timeline" className="relative overflow-hidden rounded-2xl border border-line bg-panel p-5">
      <div aria-hidden className="guides pointer-events-none absolute inset-0 opacity-50" />
      <h2 id="timeline" className="relative text-base">When facts stop being true</h2>
      <p className="relative mt-1 text-sm text-ash">Each bar runs from the date a fact became valid to the date it ends. Past the line, a post can&apos;t use it.</p>
      <div className="relative mt-5 pt-6">
        <div aria-hidden className="absolute inset-y-0 z-10 w-0.5 bg-bone" style={{ left: x(today) }}>
          <span className="absolute -top-0 left-1.5 whitespace-nowrap font-label text-[11px] font-bold uppercase tracking-[0.14em] text-bone">Today</span>
        </div>
        <ul className="space-y-2">
          {dated.map((f, i) => (
            <li key={f.id} className="grid grid-cols-[4.5rem_1fr] items-center gap-3" title={`${f.id}: ${f.statement} · ${fmt(f.valid_from)} to ${fmt(f.valid_until!)}`}>
              <span className="font-mono text-[11px] text-ash">{f.id}</span>
              <div className="relative h-5">
                <motion.div initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
                  transition={{ delay: i * 0.05, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                  className={`absolute inset-y-0 origin-left rounded-[3px] ${f.expired ? "bg-blocking/70" : "bg-ok/70"}`}
                  style={{ left: x(f.valid_from), width: `calc(${x(f.valid_until!)} - ${x(f.valid_from)})` }} />
                {/* Late end dates put their label inside the bar's end, so it isn't cut off. */}
                <span className={`absolute top-1/2 -translate-y-1/2 px-2 text-[11px] whitespace-nowrap ${pos(f.valid_until!) > 72 ? "-translate-x-full font-semibold text-ink" : "text-bone/80"}`} style={{ left: x(f.valid_until!) }}>
                  {f.expired ? "ended" : "ends"} {fmt(f.valid_until!)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
