"use client";

import { useMemo, useState } from "react";

import { CoverageStatement } from "@/components/CoverageStatement";
import { DiffView } from "@/components/DiffView";
import { type CardState, FindingCard } from "@/components/FindingCard";
import { HighlightedText, type Mark } from "@/components/HighlightedText";
import { IntentForm, type IntentValue } from "@/components/IntentForm";
import { IntentPanel } from "@/components/IntentPanel";
import { GROUPS, groupOf } from "@/components/severity";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { WakingBanner } from "@/components/WakingBanner";
import {
  applyFixes,
  check,
  CheckError,
  type CheckReport,
  dismissFinding,
  type Finding,
  submitForReview,
} from "@/lib/api";
import samples from "@/lib/samples.json";

const SAMPLE = samples.find((s) => s.key === "worked-example")!;
const NO_INTENT: IntentValue = { key_phrases: "", cta: "", channel: "instagram" };
const FRESH: CardState = { accepted: false, edit: null, dismissed: false };

type Row = { n: number; f: Finding; group: (typeof GROUPS)[number] };

export function CheckForm() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [intent, setIntent] = useState<IntentValue>(NO_INTENT);
  const [busy, setBusy] = useState(false);
  const [waking, setWaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<CheckReport | null>(null);
  const [cards, setCards] = useState<Record<string, CardState>>({});
  const [submitted, setSubmitted] = useState(false);
  const imageUrl = useMemo(() => (file && file.type.startsWith("image/") ? URL.createObjectURL(file) : null), [file]);

  async function run(job: () => Promise<CheckReport>) {
    setBusy(true);
    setError(null);
    try {
      const r = await job();
      setReport(r);
      setCards({});
      return r;
    } catch (err) {
      setError(err instanceof CheckError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
      setWaking(false);
    }
  }

  function onCheck(e: React.FormEvent) {
    e.preventDefault();
    const form = new FormData();
    if (file) form.set("file", file);
    else form.set("text", text);
    form.set("channel", intent.channel);
    form.set("region", "IN");
    const phrases = intent.key_phrases.split(",").map((p) => p.trim()).filter(Boolean);
    form.set("intent_json", JSON.stringify({ key_phrases: phrases, cta: intent.cta.trim() || null }));
    setSubmitted(false);
    run(() => check(form, setWaking));
  }

  const rows: Row[] = useMemo(() => {
    if (!report) return [];
    const all = [
      ...report.findings.map((f) => ({ f, group: groupOf(f, false) })),
      ...report.needs_human.map((f) => ({ f, group: groupOf(f, true) })),
    ];
    all.sort((a, b) => GROUPS.indexOf(a.group) - GROUPS.indexOf(b.group) || (a.f.span?.start ?? 1e9) - (b.f.span?.start ?? 1e9));
    return all.map((r, i) => ({ ...r, n: i + 1 }));
  }, [report]);

  const state = (f: Finding) => cards[f.id] ?? FRESH;
  const openBlocking = rows.filter((r) => r.group === "Blocking" && !state(r.f).dismissed).length;
  const count = (g: string) => rows.filter((r) => r.group === g && !state(r.f).dismissed).length;
  const accepted = rows.filter((r) => state(r.f).accepted && r.f.record_id).map((r) => r.f.record_id!);
  const edits = Object.fromEntries(
    rows.filter((r) => state(r.f).edit !== null && r.f.record_id).map((r) => [r.f.record_id!, state(r.f).edit!]),
  );
  const marks: Mark[] = rows
    .filter((r) => r.f.span && !state(r.f).dismissed)
    .map((r) => ({ n: r.n, start: r.f.span!.start, end: r.f.span!.end, group: r.group }));

  return (
    <div className="space-y-6">
      <form onSubmit={onCheck} className="space-y-3">
        <label htmlFor="draft" className="block font-medium">Paste a post, or upload a file</label>
        <Textarea id="draft" rows={5} value={text} placeholder="Paste your draft here"
          onChange={(e) => (setText(e.target.value), setFile(null))} />
        <IntentForm value={intent} onChange={setIntent} />
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" onClick={() => {
            setText(SAMPLE.text);
            setFile(null);
            setIntent({
              key_phrases: (SAMPLE.intent?.key_phrases ?? []).join(", "),
              cta: SAMPLE.intent?.cta ?? "",
              channel: "instagram",
            });
          }}>
            Load sample post
          </Button>
          <label className="text-sm">
            <span className="sr-only">Upload a file</span>
            <input type="file" accept=".txt,.md,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <Button type="submit" disabled={busy || (!text.trim() && !file)}>{busy ? "Checking…" : "Check"}</Button>
        </div>
      </form>

      {waking && <WakingBanner />}
      {error && <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">{error}</p>}
      {submitted && (
        <p role="status" className="rounded-md border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-900">
          Submitted for review. Reviewers can now see this version.
        </p>
      )}

      {report && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="min-w-0 space-y-6">
            <section aria-label="Your draft" className="rounded-lg border p-4">
              <HighlightedText text={report.checked_text ?? text} marks={marks} />
            </section>
            {imageUrl && (
              <section aria-label="Image" className="rounded-lg border p-4">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={imageUrl} alt="The uploaded image (its findings are listed with the others)" className="max-h-64 w-auto" />
              </section>
            )}
            {report.previous_text && report.checked_text && <DiffView before={report.previous_text} after={report.checked_text} />}
            <IntentPanel intent={report.intent} suggested={report.suggested_text} />
          </div>

          <div className="min-w-0 space-y-4">
            <p className="text-lg">
              <strong data-testid="blocking-count" data-count={openBlocking}>
                {openBlocking === 0 ? "Nothing blocks publishing in the checks that ran" : `${openBlocking} ${openBlocking === 1 ? "issue blocks" : "issues block"} publishing`}
              </strong>{" "}
              · {count("Major")} major · {count("Minor")} minor · {count("Needs human eyes")} {count("Needs human eyes") === 1 ? "needs" : "need"} human eyes · {count("Advisory")} advisory
            </p>
            {GROUPS.map((g) => {
              const items = rows.filter((r) => r.group === g);
              if (!items.length) return null;
              return (
                <section key={g} aria-label={g} className="space-y-3">
                  <h2 className="font-semibold">{g}</h2>
                  {items.map((r) => (
                    <FindingCard key={r.f.id} n={r.n} f={r.f} group={r.group} state={state(r.f)}
                      onChange={(s) => setCards((c) => ({ ...c, [r.f.id]: s }))}
                      onDismiss={async (reason) => {
                        try {
                          await dismissFinding(r.f.record_id!, reason);
                          setCards((c) => ({ ...c, [r.f.id]: { ...state(r.f), dismissed: true } }));
                        } catch (err) {
                          setError(err instanceof CheckError ? err.message : "Couldn't dismiss it. Try again.");
                        }
                      }} />
                  ))}
                </section>
              );
            })}
            <div className="sticky bottom-0 flex flex-wrap gap-3 border-t bg-background py-3">
              <Button variant="outline" disabled={busy || !report.version_id || (!accepted.length && !Object.keys(edits).length)}
                onClick={() => run(() => applyFixes(report.version_id!, accepted, edits, setWaking))}>
                Apply accepted fixes &amp; re-check
              </Button>
              <Button disabled={busy || openBlocking > 0 || !report.content_id}
                title={openBlocking > 0 ? "Fix, edit or remove the blocking issues first." : undefined}
                onClick={async () => {
                  const r = await run(() => submitForReview(report.content_id!, setWaking));
                  if (r) setSubmitted(true);
                }}>
                {openBlocking > 0 ? `Submit for review (${openBlocking} blocking left)` : "Submit for review"}
              </Button>
            </div>
            <CoverageStatement coverage={report.coverage} />
          </div>
        </div>
      )}
    </div>
  );
}
