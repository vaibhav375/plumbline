import type { CheckReport, Finding } from "@/lib/api";

const SEVERITY: Record<string, string> = {
  blocking: "border-red-300 bg-red-50 text-red-900",
  major: "border-amber-300 bg-amber-50 text-amber-900",
  minor: "border-slate-300 bg-slate-50 text-slate-800",
};
const ORDER: Record<string, number> = { blocking: 0, major: 1, minor: 2 };

function FindingCard({ f }: { f: Finding }) {
  return (
    <li className="rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className={`rounded border px-2 py-0.5 font-medium capitalize ${SEVERITY[f.severity] ?? ""}`}>
          {f.severity}
        </span>
        {f.advisory && <span className="rounded border px-2 py-0.5 text-muted-foreground">Advisory</span>}
        <span className="font-mono text-xs">{f.rule_id ?? f.fact_id}</span>
        <span className="text-muted-foreground">{f.category}</span>
      </div>
      {f.quote ? (
        <p className="mt-2">
          <mark className="rounded bg-yellow-100 px-1">“{f.quote}”</mark>
        </p>
      ) : f.image_id ? (
        <p className="mt-2 text-sm text-muted-foreground">Image {f.image_id}</p>
      ) : null}
      <p className="mt-2">{f.explanation}</p>
      {f.fix?.text && (
        <p className="mt-1 text-sm">
          Suggested: <span className="font-medium">{f.fix.text}</span>
        </p>
      )}
      <p className="mt-1 text-xs text-muted-foreground">Basis: {f.basis_excerpt}</p>
    </li>
  );
}

export function FindingList({ report }: { report: CheckReport }) {
  const findings = [...report.findings].sort(
    (a, b) => (ORDER[a.severity] ?? 3) - (ORDER[b.severity] ?? 3),
  );
  const count = (s: string) => findings.filter((f) => f.severity === s).length;
  const cov = report.coverage;
  return (
    <section aria-labelledby="results" className="space-y-6">
      <div>
        <h2 id="results" className="text-lg font-semibold">
          Findings
        </h2>
        <p className="text-sm text-muted-foreground">
          {count("blocking")} blocking · {count("major")} major · {count("minor")} minor · code checks in{" "}
          {report.ms_code} ms
        </p>
      </div>
      {findings.length === 0 ? (
        <p>No findings from the {cov.rules_run.length} rules that ran. See what wasn&apos;t checked below.</p>
      ) : (
        <ul className="space-y-3">
          {findings.map((f) => (
            <FindingCard key={f.id} f={f} />
          ))}
        </ul>
      )}
      <div className="rounded-lg border p-4">
        <h2 className="font-semibold">Not checked</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
          {cov.not_checked.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        {cov.ai_status !== "ok" && cov.ai_note && <p className="mt-3 text-sm">{cov.ai_note}</p>}
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">
            {cov.rules_run.length} rules ran · {Object.keys(cov.rules_not_run).length} not run
          </summary>
          <ul className="mt-2 space-y-1">
            {Object.entries(cov.rules_not_run).map(([id, why]) => (
              <li key={id}>
                <span className="font-mono text-xs">{id}</span>: {why}
              </li>
            ))}
          </ul>
        </details>
      </div>
    </section>
  );
}
