"use client";

import { useMemo, useState } from "react";

import { CoverageStatement } from "@/components/CoverageStatement";
import { DiffView } from "@/components/DiffView";
import { type CardState, FindingCard } from "@/components/FindingCard";
import { HighlightedText, type Mark } from "@/components/HighlightedText";
import { type Box, ImageWithBoxes } from "@/components/ImageWithBoxes";
import { IntentForm, type IntentValue } from "@/components/IntentForm";
import { IntentPanel } from "@/components/IntentPanel";
import { SeverityTiles } from "@/components/charts/SeverityTiles";
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
  escalateFinding,
  type Finding,
  submitForReview,
} from "@/lib/api";
import replay from "@/lib/sample-replay.json";
import samples from "@/lib/samples.json";

const SAMPLE = samples.find((s) => s.key === "worked-example")!;
const NO_INTENT: IntentValue = { key_phrases: "", cta: "", channel: "instagram" };
const FRESH: CardState = { accepted: false, edit: null, dismissed: false };
// On narrow screens results land below the form; bring them into view so the click visibly did something.
const showResults = () =>
  requestAnimationFrame(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" }));

const REPLAY_DATE = new Date(replay.captured_at).toLocaleDateString("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "Asia/Kolkata",
});

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
  const [altText, setAltText] = useState("");
  const [decorative, setDecorative] = useState(false);
  // The sample opens as a stored report of a real run: instant, and the same every time.
  const [isReplay, setIsReplay] = useState(false);
  const imageUrl = useMemo(() => (file && file.type.startsWith("image/") ? URL.createObjectURL(file) : null), [file]);

  async function run(job: () => Promise<CheckReport>) {
    setBusy(true);
    setError(null);
    try {
      const r = await job();
      setReport(r);
      setCards({});
      setIsReplay(false);
      showResults();
      return r;
    } catch (err) {
      setError(err instanceof CheckError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
      setWaking(false);
    }
  }

  function onCheck(e?: React.FormEvent) {
    e?.preventDefault();
    const form = new FormData();
    if (file) form.set("file", file);
    else form.set("text", text);
    if (imageUrl) {
      form.set("alt_text", altText);
      form.set("decorative", String(decorative));
    }
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
  // Blocking findings stay open until fixed by a re-check or sent to a reviewer.
  const openBlocking = rows.filter((r) => r.group === "Blocking" && !state(r.f).dismissed && !state(r.f).escalated).length;
  const blockingTotal = rows.filter((r) => r.group === "Blocking").length;
  const count = (g: string) => rows.filter((r) => r.group === g && !state(r.f).dismissed).length;
  const accepted = rows.filter((r) => state(r.f).accepted && r.f.record_id).map((r) => r.f.record_id!);
  const edits = Object.fromEntries(
    rows.filter((r) => state(r.f).edit !== null && r.f.record_id).map((r) => [r.f.record_id!, state(r.f).edit!]),
  );
  const boxes: Box[] = rows
    .filter((r) => r.f.bbox && !state(r.f).dismissed)
    .map((r) => ({ n: r.n, bbox: r.f.bbox as Box["bbox"], group: r.group }));
  // An accepted fix or an edit shows in the draft straight away, before it is applied.
  const replacementOf = (r: Row): string | undefined => {
    const st = state(r.f);
    if (st.edit !== null) return st.edit;
    if (st.accepted && r.f.fix) return r.f.fix.kind === "remove" ? "" : (r.f.fix.text ?? undefined);
    return undefined;
  };
  const marks: Mark[] = rows
    .filter((r) => r.f.span && !state(r.f).dismissed)
    .map((r) => ({ n: r.n, start: r.f.span!.start, end: r.f.span!.end, group: r.group, replacement: replacementOf(r) }));
  const pendingFixes = accepted.length + Object.keys(edits).length;

  return (
    <div className="space-y-6">
      <form onSubmit={onCheck} className="space-y-3">
        <label htmlFor="draft" className="block font-medium">Paste a post, or upload a file</label>
        <Textarea id="draft" rows={5} value={text} placeholder="Paste your draft here"
          onChange={(e) => (setText(e.target.value), setFile(null))} />
        <IntentForm value={intent} onChange={setIntent} />
        {imageUrl && (
          <fieldset className="space-y-2 rounded-md border p-3">
            <legend className="px-1 text-sm font-medium">Image description</legend>
            <label htmlFor="alt-text" className="block text-sm">
              Alt text: what must someone who can&apos;t see this image learn from it?
            </label>
            <Textarea id="alt-text" rows={2} value={altText} disabled={decorative} placeholder="Leave empty and the check will ask for it"
              onChange={(e) => setAltText(e.target.value)} />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={decorative} onChange={(e) => setDecorative(e.target.checked)} />
              Decorative only: it carries no information, so screen readers skip it
            </label>
          </fieldset>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" onClick={() => {
            setText(SAMPLE.text);
            setFile(null);
            setIntent({
              key_phrases: (SAMPLE.intent?.key_phrases ?? []).join(", "),
              cta: SAMPLE.intent?.cta ?? "",
              channel: "instagram",
            });
            setReport(replay.report as unknown as CheckReport);
            setCards({});
            setSubmitted(false);
            setError(null);
            setIsReplay(true);
            showResults();
          }}>
            Open the sample post
          </Button>
          <label className="text-sm">
            <span className="sr-only">Upload a file</span>
            <input type="file" accept=".txt,.md,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              className="text-sm file:mr-3 file:rounded-md file:border file:border-border file:bg-background file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-muted"
              onChange={(e) => (setFile(e.target.files?.[0] ?? null), setAltText(""), setDecorative(false))} />
          </label>
          <Button type="submit" disabled={busy || (!text.trim() && !file)}>{busy ? "Checking…" : "Check"}</Button>
        </div>
      </form>

      <div id="results" className="scroll-mt-20 space-y-6 lg:scroll-mt-4">
      {isReplay && report && (
        <div role="note" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-accent-brand/40 bg-white px-4 py-3 text-sm">
          <p>
            <strong>Replay of a real check run on {REPLAY_DATE}</strong> (it took {Math.round(replay.report.ms_total / 1000)} s
            live). Nothing here is saved, so fixes and submitting are off. Run it live to check the post now and act on it.
          </p>
          <Button type="button" disabled={busy} onClick={() => onCheck()}>{busy ? "Checking…" : "Run it live"}</Button>
        </div>
      )}
      {waking && <WakingBanner />}
      {error && <p role="alert" className="rounded-lg border border-blocking/40 bg-white px-4 py-3 text-sm text-blocking">{error}</p>}
      {submitted && (
        <p role="status" data-version-id={report?.version_id ?? ""}
          className="rounded-lg border border-ok/40 bg-white px-4 py-3 text-sm text-ok">
          Submitted for review. Reviewers can now see this version.
        </p>
      )}

      {report && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="min-w-0 space-y-6">
            <section aria-label="Your draft" className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
              <HighlightedText text={report.checked_text ?? text} marks={marks} />
            </section>
            {imageUrl && (
              <section aria-label="Image" className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
                <ImageWithBoxes src={imageUrl} boxes={boxes} />
              </section>
            )}
            {report.previous_text && report.checked_text && <DiffView before={report.previous_text} after={report.checked_text} />}
            <IntentPanel intent={report.intent} suggested={report.suggested_text} />
          </div>

          <div className="min-w-0 space-y-4">
            <p className="text-lg">
              <strong data-testid="blocking-count" data-count={blockingTotal}>
                {blockingTotal === 0
                  ? "Nothing blocks publishing in the checks that ran"
                  : `${blockingTotal} ${blockingTotal === 1 ? "issue blocks" : "issues block"} publishing`}
              </strong>{" "}
              · {count("Major")} major · {count("Minor")} minor · {count("Needs human eyes")} {count("Needs human eyes") === 1 ? "needs" : "need"} human eyes · {count("Advisory")} advisory
            </p>
            <SeverityTiles counts={Object.fromEntries(GROUPS.map((g) => [g, count(g)])) as Record<(typeof GROUPS)[number], number>} />
            {GROUPS.map((g) => {
              const items = rows.filter((r) => r.group === g);
              if (!items.length) return null;
              return (
                <section key={g} aria-label={g} className="space-y-3">
                  <h2 className="font-semibold">{g}</h2>
                  {items.map((r) => (
                    <FindingCard key={r.f.id} n={r.n} f={r.f} group={r.group} state={state(r.f)}
                      onChange={(s) => setCards((c) => ({ ...c, [r.f.id]: s }))}
                      onEscalate={async (reason) => {
                        try {
                          await escalateFinding(r.f.record_id!, reason);
                          setCards((c) => ({ ...c, [r.f.id]: { ...state(r.f), escalated: true } }));
                        } catch (err) {
                          setError(err instanceof CheckError ? err.message : "Couldn't send it. Try again.");
                        }
                      }}
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
              <Button variant={pendingFixes ? "default" : "outline"} disabled={busy || !report.version_id || !pendingFixes}
                className={pendingFixes ? "change-in" : undefined}
                onClick={() => run(() => applyFixes(report.version_id!, accepted, edits, setWaking))}>
                Apply my fixes and check again
                {pendingFixes > 0 && (
                  <span className="ml-1 rounded-full bg-white px-2 text-xs font-bold text-accent-brand" aria-label={`${pendingFixes} ready`}>{pendingFixes}</span>
                )}
              </Button>
              <Button disabled={busy || openBlocking > 0 || !report.content_id}
                title={openBlocking > 0 ? "Fix the blocking issues, or ask a reviewer about each one." : undefined}
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
    </div>
  );
}
