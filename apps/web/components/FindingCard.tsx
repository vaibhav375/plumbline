"use client";

import { ArrowDown, Check } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { HEX, TAG, type Group } from "@/components/severity";
import { Button } from "@/components/ui/button";
import type { Finding } from "@/lib/api";
import { useRuleTitle } from "@/lib/rule-titles";

const METHOD: Record<string, string> = { code: "Checked by rule", ai: "Checked by AI", "ai+code": "AI, confirmed by rule" };
const NOT_DISMISSIBLE = "Blocking findings can't be dismissed. Fix or edit the text, or submit it for a reviewer.";
const FIELD = "mt-1 w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone placeholder:text-ash focus:border-iris focus:outline-none";
const LABEL = "font-label text-[11px] font-semibold uppercase text-ash";

export type CardState = { accepted: boolean; edit: string | null; dismissed: boolean; escalated?: boolean };

export function FindingCard({
  n,
  f,
  group,
  state,
  active = false,
  onHover,
  onChange,
  onDismiss,
  onEscalate,
}: {
  n: number;
  f: Finding;
  group: Group;
  state: CardState;
  active?: boolean;
  onHover?: (n: number | null) => void;
  onChange: (s: CardState) => void;
  onDismiss: (reason: string) => Promise<void>;
  onEscalate?: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState<string | null>(null);
  const ruleTitle = useRuleTitle(f.rule_id);
  const [ask, setAsk] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const fix = f.fix && f.fix.kind !== "none" ? f.fix : null;
  const canChange = Boolean(f.record_id) && !state.dismissed;
  const blocking = f.severity === "blocking" && !f.advisory;
  const color = HEX[group];
  const done = state.accepted || state.escalated;
  return (
    <motion.article id={`finding-${n}`} layout="position" aria-label={`Finding ${n}: ${f.rule_id ?? f.fact_id ?? "finding"}`}
      onMouseEnter={() => onHover?.(n)} onMouseLeave={() => onHover?.(null)} onFocus={() => onHover?.(n)}
      className={`relative scroll-mt-24 overflow-hidden rounded-xl bg-panel p-4 pl-5 ring-1 transition-[box-shadow,opacity] duration-300 ${active ? "ring-bone/40 shadow-[0_0_0_1px_rgb(237_235_230/0.15),0_18px_40px_-18px_rgb(0_0_0/0.9)]" : "ring-line"} ${state.dismissed ? "opacity-55" : ""}`}>
      <span aria-hidden className="absolute inset-y-0 left-0 w-1" style={{ background: color }} />
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span aria-hidden className="inline-flex size-7 items-center justify-center rounded-full font-label text-sm font-bold text-ink" style={{ background: color }}>
          {done ? <Check className="size-4" /> : n}
        </span>
        <span className="sr-only">{n}</span>
        <span className={`rounded border px-2 py-0.5 font-label text-[11px] font-semibold uppercase ${TAG[group]}`}>{group}</span>
        {f.tier && (
          <span className="rounded border border-line px-2 py-0.5 text-bone/80">
            {f.tier === "mandatory" ? "Mandatory" : "Brand"} {f.category}
          </span>
        )}
        <span className="rounded border border-line px-2 py-0.5 text-ash">
          {METHOD[f.method] ?? f.method}
          {f.model ? ` · ${f.model}` : ""}
        </span>
        <span className="ml-auto font-mono text-[11px] text-ash">{[f.rule_id, f.fact_id].filter(Boolean).join(" · ")}</span>
      </div>

      {f.quote ? (
        <p className="paper mt-3 rounded-md px-3 py-2 text-[15px] font-medium leading-relaxed text-ink"
          style={{ boxShadow: `inset 0 -3px 0 ${color}` }}>“{f.quote}”</p>
      ) : f.image_id && <p className="mt-3 text-sm">Image {f.image_id}</p>}
      {ruleTitle && <p className="mt-3 text-sm font-semibold text-bone">Rule: {ruleTitle}</p>}
      <p className="mt-2 text-[15px] leading-relaxed text-bone">{f.explanation}</p>
      {f.claim_status && <p className="mt-1 text-xs text-ash">Claim {f.claim_status.replace("_", " ")}</p>}
      <p className="mt-2 border-l border-line pl-3 text-xs leading-relaxed text-ash"><span className={LABEL}>Source </span>{f.basis_excerpt}</p>

      {(fix || f.fix?.note) && (
        <div className={`mt-4 rounded-lg border p-3 text-sm transition-colors duration-500 ${state.accepted ? "border-ok/60 bg-ok/[0.07]" : "border-line bg-carbon/60"}`}>
          <p className={LABEL}>{fix?.kind === "approved_wording" ? `Approved wording ${fix.ref_id}` : "Suggested fix"}</p>
          {fix && f.quote && (
            <div className="mt-2 grid gap-1">
              <p className="relative w-fit text-bone/60">
                {f.quote}
                <motion.span aria-hidden className="absolute inset-x-0 top-1/2 h-[2px] origin-left bg-blocking"
                  initial={false} animate={{ scaleX: state.accepted ? 1 : 0 }} transition={{ duration: 0.45, ease: [0.65, 0, 0.35, 1] }} />
              </p>
              <ArrowDown aria-hidden className={`size-3.5 transition-colors ${state.accepted ? "text-ok" : "text-ash"}`} />
              <p className={`font-semibold transition-colors duration-500 ${state.accepted ? "text-ok" : "text-bone"}`}>
                {fix.kind === "remove" ? "Remove this sentence." : fix.text}
              </p>
            </div>
          )}
          {fix && !f.quote && (fix.kind === "remove" ? <p className="mt-1">Remove this sentence.</p> : fix.text && <p className="mt-1 font-semibold">{fix.text}</p>)}
          {f.fix?.note && <p className="mt-2 text-xs text-ash">{f.fix.note}</p>}
          <AnimatePresence>
            {state.accepted && fix && (
              <motion.p key="ready" role="status" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden text-sm">
                <span className="mt-3 flex items-center gap-1.5 border-t border-ok/30 pt-2 font-label text-xs font-semibold uppercase text-ok">
                  <Check className="size-3.5" aria-hidden /> Ready to apply
                </span>
                <span className="mt-1 block text-xs text-ash">It&apos;s shown in your draft now. Apply your fixes to update the post and check it again.</span>
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      )}

      {state.dismissed ? (
        <p className="mt-3 text-sm text-ash">Dismissed.</p>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          {fix && (
            <Button size="sm" variant={state.accepted ? "default" : "outline"} disabled={!canChange}
              className={state.accepted ? "bg-ok text-carbon before:bg-ok hover:text-carbon" : undefined}
              aria-pressed={state.accepted} onClick={() => onChange({ ...state, accepted: !state.accepted, edit: null })}>
              {state.accepted && <Check aria-hidden />}
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
          {blocking && onEscalate && (
            state.escalated ? (
              <span className="self-center font-label text-xs font-semibold uppercase text-iris">Sent to a reviewer</span>
            ) : (
              <Button size="sm" variant="outline" disabled={!canChange} onClick={() => setAsk("")}>
                Ask a reviewer
              </Button>
            )
          )}
        </div>
      )}
      {ask !== null && onEscalate && (
        <form className="mt-3 flex flex-wrap items-end gap-2 text-sm"
          onSubmit={async (e) => {
            e.preventDefault();
            setSending(true);
            try {
              await onEscalate(ask);
              setAsk(null);
            } finally {
              setSending(false);
            }
          }}>
          <label className="grow">
            What should the reviewer know? (required)
            <input className={FIELD} value={ask} onChange={(e) => setAsk(e.target.value)} />
          </label>
          <Button size="sm" type="submit" disabled={!ask.trim() || sending}>{sending ? "Sending…" : "Send to a reviewer"}</Button>
          <Button size="sm" type="button" variant="ghost" onClick={() => setAsk(null)}>Cancel</Button>
        </form>
      )}
      {state.edit !== null && !state.dismissed && (
        <label className="mt-3 block text-sm">
          Replace “{f.quote}” with (leave empty to remove it)
          <input className={FIELD} value={state.edit}
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
            <input className={FIELD} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <Button size="sm" type="submit" disabled={!reason.trim()}>Dismiss with reason</Button>
          <Button size="sm" type="button" variant="ghost" onClick={() => setReason(null)}>Cancel</Button>
        </form>
      )}
    </motion.article>
  );
}
