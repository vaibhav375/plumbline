import { IntervalChart, type Row } from "@/components/charts/IntervalChart";
import { PageHeader } from "@/components/PageHeader";
import latest from "@/public/eval/latest.json";

type Result = {
  recall: number;
  precision: number;
  false_alarms_per_clean: number;
  citation_valid_rate: number;
  injection_recall_delta: number;
  ms_p95: number;
  unavailable: number;
  intervals: Record<string, [number, number]>;
  counts: Record<string, [number, number]>;
};
type Egress = { provider: string; model: string; region: string; calls: number; chars_sent: number; tasks: Record<string, number>; statuses: Record<string, number> };
type Latest = {
  generated_at: string;
  today: string;
  rulebook_version: string;
  dataset: { name: string; n_items: number; n_labels: number; kinds: Record<string, number> };
  results: { plumbline: Result; baseline: Result };
  egress: { plumbline: Egress[]; baseline: Egress[] };
};
const data = latest as unknown as Latest;
// India time, so a late-evening run isn't shown with the next day's (UTC) date.
const RUN_AT = new Date(data.generated_at).toLocaleString("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Asia/Kolkata",
});

const pct = (x: number) => `${Math.round(x * 100)}%`;

const COMPARE: Row[] = (
  [
    ["Problems found", "recall"],
    ["Findings that were right", "precision"],
    ["Clean posts with a false alarm", "clean_with_alarm"],
  ] as const
).map(([label, key]) => ({
  label,
  points: (["plumbline", "baseline"] as const).map((m) => {
    const [k, n] = data.results[m].counts[key];
    const [lo, hi] = data.results[m].intervals[key];
    return { value: k / Math.max(1, n), lo, hi, label: `${k}/${n}`, tip: `${m === "plumbline" ? "Plumbline" : "Baseline"}: ${k} of ${n} (${pct(k / Math.max(1, n))}); 95% interval ${pct(lo)}–${pct(hi)}` };
  }),
}));
const interval = ([lo, hi]: [number, number]) => `95% interval ${pct(lo)}–${pct(hi)}`;

const STEPS = [
  { title: "Paste or upload", body: "Text, DOCX, PDF or an image; images are read with OCR." },
  { title: "Code checks", body: "Rule patterns, term list, contrast, alt text, and confidential facts, matched in code only." },
  { title: "AI checks", body: "Claim extraction and judgement rules (Groq, then Gemini if it fails)." },
  { title: "Validators", body: "Every AI finding must cite an ID that exists and a quote that is really there; a second model checks it." },
  { title: "Findings and fixes", body: "Cited findings, approved-wording fixes, and a list of what wasn't checked." },
  { title: "Review and audit", body: "Routed approvals, row-level security, and a hash-chained audit log." },
];

function MetricCard({ name, help, metric, better }: { name: string; help: string; metric: keyof typeof KEYS; better: string }) {
  const { value, count, show } = KEYS[metric];
  return (
    <section aria-label={name} className="space-y-3 rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
      <div>
        <h3 className="font-semibold">{name}</h3>
        <p className="text-xs text-muted-foreground">{help} {better}</p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        {(["plumbline", "baseline"] as const).map((mode) => {
          const r = data.results[mode];
          return (
            <div key={mode} className={`rounded-md border p-3 ${mode === "plumbline" ? "bg-muted/40" : ""}`}>
              <dt className="text-xs font-medium">{mode === "plumbline" ? "Plumbline" : "Baseline"}</dt>
              <dd className="text-2xl font-semibold tabular-nums" data-testid={`${metric}-${mode}`}>{show(value(r))}</dd>
              {count && (
                <dd className="text-xs tabular-nums">
                  {r.counts[count][0]} / {r.counts[count][1]} · {interval(r.intervals[count])}
                </dd>
              )}
            </div>
          );
        })}
      </dl>
    </section>
  );
}

const KEYS = {
  recall: { value: (r: Result) => r.recall, count: "recall", show: pct },
  precision: { value: (r: Result) => r.precision, count: "precision", show: pct },
  clean: { value: (r: Result) => r.counts.clean_with_alarm[0] / Math.max(1, r.counts.clean_with_alarm[1]), count: "clean_with_alarm", show: pct },
  citations: { value: (r: Result) => r.citation_valid_rate, count: "citation_valid", show: pct },
  injection: {
    value: (r: Result) => r.injection_recall_delta,
    count: null,
    show: (x: number) => `${x > 0 ? "+" : x < 0 ? "−" : "±"}${Math.round(Math.abs(x) * 100)} pts`,
  },
  latency: { value: (r: Result) => r.ms_p95, count: null, show: (x: number) => `${(x / 1000).toFixed(1)} s` },
} as const;

function EgressTable({ rows, label }: { rows: Egress[]; label: string }) {
  return (
    <div className="overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-ink/5">
      <table className="w-full text-left text-sm">
        <caption className="px-3 py-2 text-left text-xs text-muted-foreground">{label}</caption>
        <thead className="bg-muted/50">
          <tr>
            {["Provider", "Model", "Region", "Calls", "Characters sent", "Purpose", "Outcome"].map((h) => (
              <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => (
            <tr key={`${e.provider}-${e.model}`} className="border-t align-top">
              <td className="px-3 py-2">{e.provider}</td>
              <td className="px-3 py-2 font-mono text-xs">{e.model}</td>
              <td className="px-3 py-2">{e.region}</td>
              <td className="px-3 py-2 tabular-nums">{e.calls}</td>
              <td className="px-3 py-2 tabular-nums">{e.chars_sent.toLocaleString("en-IN")}</td>
              <td className="px-3 py-2">{Object.entries(e.tasks).map(([k, v]) => `${k} ${v}`).join(", ")}</td>
              <td className="px-3 py-2">{Object.entries(e.statuses).map(([k, v]) => `${k} ${v}`).join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AboutPage() {
  const d = data.dataset;
  return (
    <main className="mx-auto max-w-6xl space-y-8 p-4 sm:p-6">
      <PageHeader title="How I know it works" subtitle="How Plumbline was tested against a simpler AI approach, the results, and what data leaves the system." />

      <section aria-labelledby="architecture" className="space-y-3">
        <h2 id="architecture" className="text-lg font-semibold">How a check runs</h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-3">
              <p className="text-sm font-semibold">{i + 1}. {s.title}</p>
              <p className="text-sm text-muted-foreground">{s.body}</p>
            </li>
          ))}
        </ol>
        <p className="text-xs text-muted-foreground">
          Web app on Vercel (Next.js) · checker service on Render (FastAPI, Tesseract) · Supabase Postgres in Mumbai with
          row-level security. The checker reads and writes as the signed-in user, so the database decides what it can see.
        </p>
      </section>

      <section aria-labelledby="results" className="space-y-3">
        <h2 id="results" className="text-lg font-semibold">Results on the dev set</h2>
        <p className="text-sm">
          <strong>Dev set written by the builder; held-out human-labelled set arrives in Round 3.</strong> {d.n_items} posts:{" "}
          {d.kinds.labelled} with {d.n_labels} labelled problems in all, {d.kinds.clean} clean controls and {d.kinds.injection}{" "}
          copies with prompt-injection text added. A finding counts only if it names the right rule or fact and points at the
          right words. The baseline is one model call per post with the whole brand book and no validators; like Plumbline,
          it is never shown confidential facts. Run on {RUN_AT} IST with rulebook{" "}
          <span className="font-mono">{data.rulebook_version}</span>; dates are judged as of {data.today}.
        </p>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-ink/5">
          <IntervalChart
            series={[{ name: "Plumbline", color: "#4B3FD1" }, { name: "Baseline (one AI call, whole brand book)", color: "#0C9A8F" }]}
            caption="Dots are the measured share; lines are 95% intervals. Higher is better for the first two rows, lower for the last. The cards below have the counts."
            rows={COMPARE}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <MetricCard metric="recall" name="Problems found" help="Share of labelled problems flagged at the right words." better="Higher is better." />
          <MetricCard metric="precision" name="Findings that were right" help="Share of findings on labelled posts that matched a label." better="Higher is better." />
          <MetricCard metric="clean" name="Clean posts with a false alarm" help="Clean controls that got at least one finding." better="Lower is better." />
          <MetricCard metric="citations" name="Citations that check out" help="Findings whose rule or fact ID exists and whose quote is really in the post." better="Higher is better." />
          <MetricCard metric="injection" name="Recall change under prompt injection" help="Recall on the injected copies minus recall on their originals." better="Zero is best; negative means the injection worked." />
          <MetricCard metric="latency" name="Time per post (95th percentile)" help="From text in to findings out, including model calls." better="Lower is better." />
        </div>
      </section>

      <section aria-labelledby="egress" className="space-y-3">
        <h2 id="egress" className="text-lg font-semibold">What leaves this system</h2>
        <p className="text-sm">
          Every model call is logged with its provider, model, region, purpose, character count and outcome; the log has no
          field for the text itself. Confidential and embargoed facts are matched in code and never sent to a model, and
          Plumbline masks names and contact details before any text leaves (the baseline sends posts as they are). These
          are the calls this evaluation made.
        </p>
        <EgressTable rows={data.egress.plumbline} label="Plumbline run" />
        <EgressTable rows={data.egress.baseline} label="Baseline run" />
        <p className="rounded-md border px-4 py-3 text-sm">
          Aurelle, its products, people and figures are fictional. No real customer or personal data is used anywhere in
          this demo.
        </p>
      </section>
    </main>
  );
}
