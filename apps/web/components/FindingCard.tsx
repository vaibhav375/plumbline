"use client";

import { useState } from "react";

import { TONE, type Group } from "@/components/severity";
import { Button } from "@/components/ui/button";
import type { Finding } from "@/lib/api";

const METHOD: Record<string, string> = { code: "Rule engine", ai: "AI", "ai+code": "AI + rule check" };
const NOT_DISMISSIBLE = "Blocking findings can't be dismissed. Fix or edit the text, or submit it for a reviewer.";

export type CardState = { accepted: boolean; edit: string | null; dismissed: boolean };

export function FindingCard({
  n,
  f,
  group,
  state,
  onChange,
  onDismiss,
}: {
  n: number;
  f: Finding;
  group: Group;
  state: CardState;
  onChange: (s: CardState) => void;
  onDismiss: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState<string | null>(null);
  const fix = f.fix && f.fix.kind !== "none" ? f.fix : null;
  const canChange = Boolean(f.record_id) && !state.dismissed;
  const blocking = f.severity === "blocking" && !f.advisory;
  return (
    <article aria-label={`Finding ${n}: ${f.rule_id ?? f.fact_id ?? "finding"}`}
      className={`rounded-lg border p-4 ${state.dismissed ? "opacity-60" : ""}`}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-semibold">{n}</span>
        <span className={`rounded border px-2 py-0.5 font-medium ${TONE[group]}`}>{group}</span>
        <span className="rounded border px-2 py-0.5 text-muted-foreground">
          {METHOD[f.method] ?? f.method}
          {f.model ? ` · ${f.model}` : ""}
        </span>
        <span className="font-mono text-xs">{[f.rule_id, f.fact_id].filter(Boolean).join(" · ")}</span>
        {f.claim_status && <span className="text-muted-foreground">claim {f.claim_status.replace("_", " ")}</span>}
      </div>
      {f.quote ? <p className="mt-2 font-medium">“{f.quote}”</p> : f.image_id && <p className="mt-2 text-sm">Image {f.image_id}</p>}
      <p className="mt-1">{f.explanation}</p>
      <p className="mt-1 text-xs text-muted-foreground">Source: {f.basis_excerpt}</p>
      {(fix || f.fix?.note) && (
        <div className="mt-3 rounded-md border bg-muted/40 p-3 text-sm">
          {fix?.kind === "approved_wording" && <p className="text-xs text-muted-foreground">Approved wording {fix.ref_id}</p>}
          {fix?.kind === "remove" ? <p>Remove this sentence.</p> : fix?.text && <p className="font-medium">{fix.text}</p>}
          {f.fix?.note && <p className="mt-1 text-xs text-muted-foreground">{f.fix.note}</p>}
        </div>
      )}
      {state.dismissed ? (
        <p className="mt-3 text-sm text-muted-foreground">Dismissed.</p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {fix && (
            <Button size="sm" variant={state.accepted ? "default" : "outline"} disabled={!canChange}
              aria-pressed={state.accepted} onClick={() => onChange({ ...state, accepted: !state.accepted, edit: null })}>
              {state.accepted ? "Fix accepted" : "Accept fix"}
            </Button>
          )}
          <Button size="sm" variant="outline" disabled={!canChange || !f.quote}
            onClick={() => onChange({ ...state, accepted: false, edit: state.edit ?? f.quote })}>
            Edit
          </Button>
          <span title={blocking ? NOT_DISMISSIBLE : undefined}>
            <Button size="sm" variant="ghost" disabled={!canChange || blocking} onClick={() => setReason("")}>
              Dismiss
            </Button>
          </span>
          {blocking && <span className="sr-only">{NOT_DISMISSIBLE}</span>}
        </div>
      )}
      {state.edit !== null && !state.dismissed && (
        <label className="mt-3 block text-sm">
          Replace “{f.quote}” with (leave empty to remove it)
          <input className="mt-1 w-full rounded border px-2 py-1" value={state.edit}
            onChange={(e) => onChange({ ...state, edit: e.target.value })} />
        </label>
      )}
      {reason !== null && (
        <form className="mt-3 flex flex-wrap items-end gap-2 text-sm"
          onSubmit={async (e) => {
            e.preventDefault();
            await onDismiss(reason);
            setReason(null);
          }}>
          <label className="grow">
            Why dismiss it? (required)
            <input className="mt-1 w-full rounded border px-2 py-1" value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <Button size="sm" type="submit" disabled={!reason.trim()}>Dismiss with reason</Button>
          <Button size="sm" type="button" variant="ghost" onClick={() => setReason(null)}>Cancel</Button>
        </form>
      )}
    </article>
  );
}
