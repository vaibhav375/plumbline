"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type ImportResult, rulebook, type RulesResponse } from "@/lib/api";

const CLS: Record<string, string> = { A: "A · code", B: "B · AI judgement", C: "C · not run" };
// Class colours always sit beside their letter and count, never alone.
const CLS_HEX: Record<string, string> = { A: "#A39CFF", B: "#74A7F0", C: "#9B9AA1" };
const PILL = "inline-block rounded border px-2 py-0.5 font-label text-[11px] font-semibold uppercase tracking-[0.12em]";

function ImportPanel({ onImported }: { onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(dryRun: boolean) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const r = await rulebook.importCsv(file, dryRun);
      setResult(r);
      if (!dryRun) onImported();
    } catch (e) {
      setError(e instanceof CheckError ? e.message : "Couldn't import the file. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="import" className="space-y-3 rounded-xl border border-dashed border-line bg-panel p-5">
      <h2 id="import" className="text-base">Import CSV</h2>
      <p className="text-sm text-muted-foreground">
        Same columns as the seed rulebook. Rows are added or updated by ID, never deleted. Preview first: nothing changes until you import.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm">
          <span className="sr-only">Rules CSV file</span>
          <input type="file" accept=".csv,text/csv" className="text-sm text-ash file:mr-3 file:h-8 file:cursor-pointer file:rounded-md file:border-[1.5px] file:border-bone/40 file:bg-transparent file:px-3 file:text-sm file:font-semibold file:text-bone hover:file:border-bone" onChange={(e) => (setFile(e.target.files?.[0] ?? null), setResult(null))} />
        </label>
        <Button variant="outline" size="sm" disabled={!file || busy} onClick={() => run(true)}>Preview</Button>
        {result?.dry_run && result.imported > 0 && (
          <Button size="sm" disabled={busy} onClick={() => run(false)}>
            Import {result.imported} {result.imported === 1 ? "rule" : "rules"}
          </Button>
        )}
      </div>
      {error && <p role="alert" className="text-sm text-blocking">{error}</p>}
      {result && (
        <div role="status" className="space-y-2 text-sm">
          <p className="font-medium" data-testid="import-result">
            {result.dry_run ? "Preview: " : ""}
            {result.imported} {result.dry_run ? "would be imported" : "imported"}, {result.need_clarification} need clarification
            {result.rejected.length ? `, ${result.rejected.length} rejected` : ""}
          </p>
          {Object.entries(result.warnings).map(([id, ws]) => (
            <p key={id}><span className="font-mono">{id}</span>: {ws.join("; ")}</p>
          ))}
          {result.rejected.map((r) => <p key={r} className="text-blocking">{r}</p>)}
        </div>
      )}
    </section>
  );
}

export function RulesTable() {
  const [data, setData] = useState<RulesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const [category, setCategory] = useState<string | null>(null);
  const load = useCallback(() => {
    rulebook.rules(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load the rulebook."));
  }, []);
  useEffect(load, [load]);
  if (error) return <p role="alert" className="rounded-lg border border-blocking/40 bg-panel px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;
  const flagged = data.rules.filter((r) => r.warnings.length).length;

  const categories = [...new Set(data.rules.map((r) => r.category))].map((c) => {
    const rs = data.rules.filter((r) => r.category === c);
    return { c, n: rs.length, by: (["A", "B", "C"] as const).map((k) => [k, rs.filter((r) => r.cls === k).length] as const), mandatory: rs.filter((r) => r.tier === "mandatory").length };
  }).sort((a, b) => b.n - a.n);
  const shown = data.rules.filter((r) => !category || r.category === category);

  return (
    <div className="space-y-6">
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Rulebook summary">
        {([["Rules", data.rules.length, "text-bone"], ["Mandatory", data.rules.filter((r) => r.tier === "mandatory").length, "text-blocking"],
          ["Brand", data.rules.filter((r) => r.tier === "brand").length, "text-iris"], ["Linter warnings", flagged, "text-major"]] as const).map(([label, n, c]) => (
          <li key={label} className="rounded-xl border border-line bg-panel p-4">
            <p className={`font-display text-4xl font-extrabold tabular-nums ${c}`}>{n}</p>
            <p className="font-label text-[11px] font-semibold uppercase tracking-[0.14em] text-ash">{label}</p>
          </li>
        ))}
      </ul>
      <p className="text-sm text-bone/80">
        Version <span className="font-mono text-iris">{data.rulebook_version}</span>.
        Mandatory rules block publishing; brand rules start as advisory and block only once they graduate.
      </p>

      <section aria-labelledby="by-category" className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="by-category" className="text-base">By category</h2>
          <p className="flex flex-wrap gap-3 text-xs text-ash">
            {Object.entries(CLS).map(([k, label]) => (
              <span key={k} className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm" style={{ background: CLS_HEX[k] }} />{label}</span>
            ))}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4" role="group" aria-label="Show rules in">
          {categories.map(({ c, n, by, mandatory }) => {
            const on = category === c;
            return (
              <button key={c} type="button" aria-pressed={on} onClick={() => setCategory(on ? null : c)}
                className={`rounded-xl border p-3 text-left transition-colors duration-300 ${on ? "border-bone/60 bg-raised" : "border-line bg-panel hover:border-bone/30"}`}>
                <span className="flex items-baseline justify-between">
                  <span className="font-label text-xs font-semibold uppercase tracking-[0.14em] text-bone">{c}</span>
                  <span className="font-display text-2xl font-extrabold tabular-nums">{n}</span>
                </span>
                <span aria-hidden className="mt-2 flex h-2 gap-0.5 overflow-hidden rounded-full">
                  {by.filter(([, k]) => k).map(([k, m]) => <span key={k} style={{ flexGrow: m, background: CLS_HEX[k] }} />)}
                </span>
                <span className="mt-1.5 block text-[11px] text-ash">
                  {by.filter(([, m]) => m).map(([k, m]) => `${k} ${m}`).join(" · ")} · {mandatory} mandatory
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {data.can_import && <ImportPanel onImported={load} />}
      <div className="overflow-x-auto rounded-xl bg-panel ring-1 ring-line">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line font-label text-[11px] uppercase tracking-[0.14em] text-ash">
            <tr>
              {["ID", "Rule", "Tier", "Class", "Check", "Maturity", "Owner"].map((h) => (
                <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id} className="border-t border-line align-top transition-colors hover:bg-white/[0.03]">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-iris">{r.id}</td>
                <td className="min-w-64 px-3 py-2">
                  <p>{r.title}</p>
                  <p className="text-xs text-ash">{r.source_ref}</p>
                  {r.warnings.map((w) => (
                    <p key={w} className="mt-1 inline-block rounded border border-major/50 bg-major/10 px-2 py-0.5 text-xs text-major">
                      Linter: {w}
                    </p>
                  ))}
                </td>
                <td className="px-3 py-2"><span className={`${PILL} ${r.tier === "mandatory" ? "border-blocking/60 text-blocking" : "border-iris/60 text-iris"}`}>{r.tier}</span></td>
                <td className="whitespace-nowrap px-3 py-2">
                  <span className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm" style={{ background: CLS_HEX[r.cls] }} />{CLS[r.cls] ?? r.cls}</span>
                </td>
                <td className="px-3 py-2">{r.check_type.replace("_", " ")}</td>
                <td className="px-3 py-2"><span className={`${PILL} ${r.maturity === "blocking" ? "border-bone/50 text-bone" : "border-line text-ash"}`}>{r.maturity}</span></td>
                <td className="px-3 py-2">{r.owner_function}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
