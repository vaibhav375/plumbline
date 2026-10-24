"use client";

import { motion } from "motion/react";
import { useMemo, useState } from "react";

import { CoverageStatement } from "@/components/CoverageStatement";
import { DiffView } from "@/components/DiffView";
import { type CardState, FindingCard } from "@/components/FindingCard";
import { HighlightedText, type Mark } from "@/components/HighlightedText";
import { type Box, ImageWithBoxes } from "@/components/ImageWithBoxes";
import { IntentForm, type IntentValue } from "@/components/IntentForm";
import { IntentPanel } from "@/components/IntentPanel";
import { SeverityTiles } from "@/components/charts/SeverityTiles";
import { GROUPS, groupOf, HEX } from "@/components/severity";
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
  // The finding under the pointer, lit up both in the draft and in its card.
  const [active, setActive] = useState<number | null>(null);
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

  // Blocking issues handled so far: a fix or edit waiting to apply, or a reviewer asked.
  const blockingRows = rows.filter((r) => r.group === "Blocking");
  const handled = blockingRows.filter((r) => replacementOf(r) !== undefined || state(r.f).escalated).length;

  return (
    <div className="space-y-8">
      <form onSubmit={onCheck} className="space-y-4">
        <div className="paper relative overflow-hidden rounded-xl">
          <div className="flex items-center justify-between gap-3 border-b border-ink/10 px-4 py-2.5">
            <label htmlFor="draft" className="font-label text-xs font-bold uppercase tracking-[0.16em] text-ink">Paste a post, or upload a file</label>
            <span className="font-label text-[11px] uppercase tracking-[0.14em] text-ink/60 tabular-nums">
              {file ? file.name : `${text.length} characters`} · {intent.channel}
            </span>
          </div>
          <textarea id="draft" rows={6} value={text} placeholder="Paste your draft here"
            className="ruled block w-full resize-y bg-transparent py-[0.85rem] pr-4 pl-14 text-[17px] text-ink placeholder:text-ink/40 focus:outline-none"
            onChange={(e) => (setText(e.target.value), setFile(null))} />
          {busy && (
            <motion.div aria-hidden className="pointer-events-none absolute inset-x-0 h-16 bg-gradient-to-b from-transparent via-accent-brand/25 to-transparent"
              initial={{ top: "-4rem" }} animate={{ top: "100%" }} transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }} />
          )}
        </div>
        <IntentForm value={intent} onChange={setIntent} />
        {imageUrl && (
          <fieldset className="space-y-2 rounded-xl border border-line bg-panel p-4">
            <legend className="px-1 font-label text-xs font-bold uppercase tracking-[0.14em] text-bone">Image description</legend>
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
          <Button type="button" variant="outline" size="lg" onClick={() => {
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
              className="max-w-64 text-sm text-ash file:mr-3 file:h-10 file:cursor-pointer file:rounded-md file:border-[1.5px] file:border-bone/40 file:bg-transparent file:px-4 file:text-sm file:font-semibold file:text-bone hover:file:border-bone"
              onChange={(e) => (setFile(e.target.files?.[0] ?? null), setAltText(""), setDecorative(false))} />
          </label>
          <Button type="submit" size="lg" className="ml-auto min-w-36" disabled={busy || (!text.trim() && !file)}>{busy ? "Checking…" : "Check"}</Button>
        </div>
      </form>

      <div id="results" className="scroll-mt-20 space-y-6 lg:scroll-mt-4">
      {isReplay && report && (
        <div role="note" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-iris/40 bg-iris/[0.07] px-4 py-3 text-sm">
          <p>
            <strong>Replay of a real check run on {REPLAY_DATE}</strong> (it took {Math.round(replay.report.ms_total / 1000)} s
            live). Nothing here is saved, so fixes and submitting are off. Run it live to check the post now and act on it.
          </p>
          <Button type="button" disabled={busy} onClick={() => onCheck()}>{busy ? "Checking…" : "Run it live"}</Button>
        </div>
      )}
      {waking && <WakingBanner />}
      {error && <p role="alert" className="rounded-xl border border-blocking/40 bg-blocking/[0.07] px-4 py-3 text-sm text-blocking">{error}</p>}
      {submitted && (
        <p role="status" data-version-id={report?.version_id ?? ""}
          className="rounded-xl border border-ok/40 bg-ok/[0.07] px-4 py-3 text-sm text-ok">
          Submitted for review. Reviewers can now see this version.
        </p>
      )}

      {report && (
        <motion.div key={report.version_id ?? "replay"} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }} className="space-y-6">
          <section aria-label="Verdict" className="relative overflow-hidden rounded-2xl border border-line bg-panel p-5 sm:p-6">
            <div aria-hidden className="guides pointer-events-none absolute inset-0 opacity-60" />
            <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:items-end">
              <div>
                <p className="font-label text-xs font-semibold uppercase tracking-[0.18em] text-ash">The verdict</p>
                <p className="mt-2 font-display text-3xl font-extrabold uppercase leading-[0.95] tracking-[-0.02em] sm:text-[2.6rem]">
                  <strong data-testid="blocking-count" data-count={blockingTotal}
                    className={blockingTotal ? "text-blocking" : "text-ok"}>
                    {blockingTotal === 0
                      ? "Nothing blocks publishing in the checks that ran"
                      : `${blockingTotal} ${blockingTotal === 1 ? "issue blocks" : "issues block"} publishing`}
                  </strong>
                </p>
                <p className="mt-3 text-sm text-bone/75">
                  {count("Major")} major · {count("Minor")} minor · {count("Needs human eyes")} {count("Needs human eyes") === 1 ? "needs" : "need"} human eyes · {count("Advisory")} advisory
                </p>
              </div>
              {blockingTotal > 0 && <BlockingMeter rows={blockingRows} handled={handled} isDone={(r) => replacementOf(r) !== undefined || Boolean(state(r.f).escalated)} />}
            </div>
            <div className="relative mt-6">
              <SeverityTiles counts={Object.fromEntries(GROUPS.map((g) => [g, count(g)])) as Record<(typeof GROUPS)[number], number>} />
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
            <div className="min-w-0 space-y-6 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto lg:pb-2">
              <section aria-label="Your draft" className="paper rounded-xl">
                <div className="flex items-center justify-between border-b border-ink/10 px-5 py-2.5 font-label text-[11px] font-semibold uppercase tracking-[0.16em] text-ink/70">
                  <span>Your draft · as checked</span>
                  <span>{marks.length} marked</span>
                </div>
                <div className="px-5 py-4">
                  <HighlightedText text={report.checked_text ?? text} marks={marks} active={active} onPick={setActive} />
                </div>
                {pendingFixes > 0 && (
                  <p className="border-t border-ink/10 px-5 py-2.5 font-label text-[11px] font-semibold uppercase tracking-[0.14em] text-[#1E7F55]">
                    {pendingFixes} {pendingFixes === 1 ? "change" : "changes"} shown · not applied yet
                  </p>
                )}
              </section>
              {imageUrl && (
                <section aria-label="Image" className="rounded-xl bg-panel p-4 ring-1 ring-line">
                  <ImageWithBoxes src={imageUrl} boxes={boxes} />
                </section>
              )}
              {report.previous_text && report.checked_text && <DiffView before={report.previous_text} after={report.checked_text} />}
              <IntentPanel intent={report.intent} suggested={report.suggested_text} />
            </div>

            <div className="min-w-0 space-y-6">
              {GROUPS.map((g) => {
                const items = rows.filter((r) => r.group === g);
                if (!items.length) return null;
                return (
                  <section key={g} aria-label={g} className="space-y-3">
                    <h2 className="flex items-center gap-2 text-base">
                      <span aria-hidden className="size-2.5 rounded-full" style={{ background: HEX[g] }} />
                      {g}
                      <span className="font-label text-xs font-semibold tracking-[0.12em] text-ash">{items.length}</span>
                    </h2>
                    {items.map((r, i) => (
                      <motion.div key={r.f.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: Math.min(r.n, 10) * 0.04 + i * 0.01, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
                        <FindingCard n={r.n} f={r.f} group={r.group} state={state(r.f)} active={active === r.n} onHover={setActive}
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
                      </motion.div>
                    ))}
                  </section>
                );
              })}
              <div className="sticky bottom-0 z-30 -mx-1 flex flex-wrap gap-3 border-t border-line bg-carbon/90 px-1 py-3 backdrop-blur">
                <Button variant={pendingFixes ? "default" : "outline"} disabled={busy || !report.version_id || !pendingFixes}
                  className={pendingFixes ? "change-in" : undefined}
                  onClick={() => run(() => applyFixes(report.version_id!, accepted, edits, setWaking))}>
                  Apply my fixes and check again
                  {pendingFixes > 0 && (
                    <span className="ml-1 rounded-full bg-accent-brand px-2 text-xs font-bold text-white" aria-label={`${pendingFixes} ready`}>{pendingFixes}</span>
                  )}
                </Button>
                <Button variant="outline" disabled={busy || openBlocking > 0 || !report.content_id}
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
        </motion.div>
      )}
      </div>
    </div>
  );
}

/** One segment per blocking issue, filling as each gets a fix, an edit, or a reviewer. */
function BlockingMeter({ rows, handled, isDone }: { rows: Row[]; handled: number; isDone: (r: Row) => boolean }) {
  return (
    <div role="img" aria-label={`${handled} of ${rows.length} blocking issues handled`}>
      <div className="flex items-baseline justify-between font-label text-xs font-semibold uppercase tracking-[0.14em] text-ash">
        <span>Blocking issues handled</span>
        <span className="font-display text-2xl font-extrabold tracking-normal text-bone tabular-nums">
          {handled}<span className="text-ash">/{rows.length}</span>
        </span>
      </div>
      <div className="mt-2 flex gap-1.5">
        {rows.map((r) => (
          <div key={r.f.id} className="relative h-3 flex-1 overflow-hidden rounded-[3px] bg-blocking/20">
            <motion.div className="absolute inset-0 origin-left bg-ok" initial={false}
              animate={{ scaleX: isDone(r) ? 1 : 0 }} transition={{ type: "spring", stiffness: 200, damping: 26 }} />
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-ash">
        {handled === rows.length ? "All handled. Apply your fixes to check the new version." : "Accept a fix, edit the words, or ask a reviewer about each one."}
      </p>
    </div>
  );
}
