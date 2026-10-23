import type { CheckReport } from "@/lib/api";

export function CoverageStatement({ coverage }: { coverage: CheckReport["coverage"] }) {
  const notRun = Object.entries(coverage.rules_not_run);
  return (
    <section aria-labelledby="not-checked" className="rounded-lg border p-4">
      <h2 id="not-checked" className="font-semibold">Not checked</h2>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
        {coverage.not_checked.map((n) => <li key={n}>{n}</li>)}
      </ul>
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer">
          {coverage.rules_run.length} rules ran ({coverage.rules_advisory.length} advisory) · {notRun.length} not run
        </summary>
        <ul className="mt-2 space-y-1">
          {notRun.map(([id, why]) => <li key={id}><span className="font-mono text-xs">{id}</span>: {why}</li>)}
        </ul>
      </details>
    </section>
  );
}
