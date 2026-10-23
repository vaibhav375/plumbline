"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type ImportResult, rulebook, type RulesResponse } from "@/lib/api";

const CLS: Record<string, string> = { A: "A · code", B: "B · AI judgement", C: "C · not run" };

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
    <section aria-labelledby="import" className="space-y-3 rounded-lg border p-4">
      <h2 id="import" className="font-semibold">Import CSV</h2>
      <p className="text-sm text-muted-foreground">
        Same columns as the seed rulebook. Rows are added or updated by ID, never deleted. Preview first: nothing changes until you import.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm">
          <span className="sr-only">Rules CSV file</span>
          <input type="file" accept=".csv,text/csv" onChange={(e) => (setFile(e.target.files?.[0] ?? null), setResult(null))} />
        </label>
        <Button variant="outline" size="sm" disabled={!file || busy} onClick={() => run(true)}>Preview</Button>
        {result?.dry_run && result.imported > 0 && (
          <Button size="sm" disabled={busy} onClick={() => run(false)}>
            Import {result.imported} {result.imported === 1 ? "rule" : "rules"}
          </Button>
        )}
      </div>
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
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
          {result.rejected.map((r) => <p key={r} className="text-red-800">{r}</p>)}
        </div>
      )}
    </section>
  );
}

export function RulesTable() {
  const [data, setData] = useState<RulesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const load = useCallback(() => {
    rulebook.rules(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load the rulebook."));
  }, []);
  useEffect(load, [load]);
  if (error) return <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-muted-foreground">Loading…</p></>;
  const flagged = data.rules.filter((r) => r.warnings.length).length;

  return (
    <div className="space-y-6">
      <p className="text-sm">
        {data.rules.length} rules · {flagged} with linter warnings · version <span className="font-mono">{data.rulebook_version}</span>.
        Mandatory rules block publishing; brand rules start as advisory and block only once they graduate.
      </p>
      {data.can_import && <ImportPanel onImported={load} />}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted/50">
            <tr>
              {["ID", "Rule", "Tier", "Class", "Check", "Maturity", "Owner"].map((h) => (
                <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rules.map((r) => (
              <tr key={r.id} className="border-t align-top">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs">{r.id}</td>
                <td className="min-w-64 px-3 py-2">
                  <p>{r.title}</p>
                  <p className="text-xs text-muted-foreground">{r.source_ref}</p>
                  {r.warnings.map((w) => (
                    <p key={w} className="mt-1 inline-block rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs text-amber-950">
                      Linter: {w}
                    </p>
                  ))}
                </td>
                <td className="px-3 py-2">{r.tier}</td>
                <td className="whitespace-nowrap px-3 py-2">{CLS[r.cls] ?? r.cls}</td>
                <td className="px-3 py-2">{r.check_type.replace("_", " ")}</td>
                <td className="px-3 py-2">{r.maturity}</td>
                <td className="px-3 py-2">{r.owner_function}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
