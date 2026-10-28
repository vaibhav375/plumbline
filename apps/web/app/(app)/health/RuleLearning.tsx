"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { CheckError, learnApi, type Draft, type RuleChange, type SavedDraft, type RuleWording } from "@/lib/api";

const FIELD = "mt-1 w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone focus:border-iris focus:outline-none";
const LABEL = "font-label text-[11px] font-semibold uppercase text-ash";
const KIND: Record<RuleChange["kind"], string> = {
  graduate: "Became blocking",
  demote: "Back to advisory",
  undo: "Graduation undone",
  unpin: "Released",
  clarify: "Reworded",
  revert: "Wording restored",
};

/** What Plumbline changed in the rulebook by itself, newest first, so nothing happens out of sight. */
export function ChangesStrip({ changes, onUndo, canUndo }: { changes: RuleChange[]; onUndo: (rule: string) => void; canUndo: (rule: string) => boolean }) {
  if (!changes.length) return null;
  return (
    <section aria-labelledby="changes" className="rounded-2xl bg-panel p-5 ring-1 ring-line">
      <h2 id="changes" className="text-lg">Changes to the rulebook</h2>
      <p className="mb-3 text-sm text-ash">Every move is also in the audit log. A rule you undo stays advisory until you release it.</p>
      <ul className="divide-y divide-line">
        {changes.slice(0, 6).map((c) => (
          <li key={c.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 py-2 text-sm" data-change={c.kind}>
            <span className="font-mono text-xs">{c.rule_id}</span>
            <strong>{KIND[c.kind]}</strong>
            <span className="text-ash">{c.why}</span>
            {(c.detail?.sample_decisions ?? 0) > 0 && (
              <span className="rounded border border-major/50 px-1.5 text-xs text-major">includes {c.detail.sample_decisions} sample decisions</span>
            )}
            <time className="ml-auto text-xs text-ash" dateTime={c.at}>{new Date(c.at).toLocaleString()}</time>
            {c.kind === "graduate" && canUndo(c.rule_id) && (
              <Button size="sm" variant="outline" onClick={() => onUndo(c.rule_id)}>Undo</Button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

const Block = ({ label, w }: { label: string; w: RuleWording }) => (
  <div className="rounded-lg border border-line bg-carbon/60 p-3 text-sm">
    <p className={LABEL}>{label}</p>
    <p className="mt-1 font-semibold">{w.title}</p>
    <p className="mt-1 text-bone/80">{w.instruction}</p>
    {w.examples_bad.map((x) => <p key={x} className="mt-1 text-xs text-blocking">Breaks it: {x}</p>)}
    {w.examples_good.map((x) => <p key={x} className="mt-1 text-xs text-ok">Follows it: {x}</p>)}
  </div>
);

const Scores = ({ s }: { s: { old: { n: number; agree: number }; new: { n: number; agree: number } } }) => (
  <p className="text-sm">
    On {s.old.n} recorded decisions the draft wasn&apos;t written from, the current wording agrees with reviewers on{" "}
    <strong>{s.old.agree}</strong>; the new wording on <strong>{s.new.agree}</strong>.
  </p>
);

/** Draft a clearer wording for a rule reviewers keep overruling, see both wordings scored on recorded decisions, then accept, edit or reject. */
export function ClarifyPanel({ rule, onDone }: { rule: string; onDone: () => void }) {
  const [draft, setDraft] = useState<Draft | SavedDraft | null>(null);
  const [edit, setEdit] = useState<RuleWording | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof CheckError ? e.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }, []);
  useEffect(() => {
    learnApi.drafts(rule).then((r) => {
      const open = r.drafts.find((d) => d.status === "draft");
      if (open) setDraft(open);
    }, () => {});
  }, [rule]);
  const w: RuleWording | null = draft ? ("new" in draft ? draft.new : draft.new_wording) : null;
  const scores = draft ? ("held_out" in draft ? draft.held_out : draft.replay) : null;
  const helps = draft && scores ? scores.new.agree > scores.old.agree : false;

  return (
    <div className="space-y-3 rounded-xl border border-line bg-panel p-4" data-testid="clarify-panel">
      {!draft && (
        <>
          <p className="text-sm">
            Plumbline reads the decisions reviewers made on this rule and their reasons, drafts a clearer wording, and tests it
            against decisions it was not written from. Nothing changes until you accept.
          </p>
          <Button size="sm" disabled={busy} onClick={() => run(async () => setDraft(await learnApi.clarify(rule)))}>
            {busy ? "Drafting… this takes about a minute" : "Draft a clearer version"}
          </Button>
        </>
      )}
      {draft && w && scores && (
        <>
          <div className="grid gap-3 md:grid-cols-2">
            <Block label="Current wording" w={"old" in draft ? draft.old : draft.old_wording} />
            <Block label="Drafted wording" w={edit ?? w} />
          </div>
          <Scores s={scores} />
          {!helps && (
            <p role="note" className="rounded-lg border border-major/50 bg-major/[0.07] px-3 py-2 text-sm text-major">
              The new wording did not agree with reviewers more often than the current one. Rejecting it is reasonable.
            </p>
          )}
          {edit && (
            <div className="space-y-2 text-sm">
              <label className="block">Title<input className={FIELD} value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></label>
              <label className="block">How to judge<textarea className={FIELD} rows={4} value={edit.instruction} onChange={(e) => setEdit({ ...edit, instruction: e.target.value })} /></label>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={busy} onClick={() => run(async () => { await learnApi.accept(draft.id, edit ?? w); setDraft(null); onDone(); })}>
              {edit ? "Accept my edit" : "Accept"}
            </Button>
            {!edit && <Button size="sm" variant="outline" onClick={() => setEdit(w)}>Edit first</Button>}
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => run(async () => { await learnApi.reject(draft.id); setDraft(null); onDone(); })}>Reject</Button>
          </div>
        </>
      )}
      {error && <p role="alert" className="text-sm text-blocking">{error}</p>}
    </div>
  );
}

export function useRuleChanges(enabled: boolean) {
  const [changes, setChanges] = useState<RuleChange[]>([]);
  const load = useCallback(() => {
    if (enabled) learnApi.changes().then((r) => setChanges(r.changes), () => {});
  }, [enabled]);
  useEffect(load, [load]);
  return { changes, reload: load };
}
