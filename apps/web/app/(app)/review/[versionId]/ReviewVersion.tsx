"use client";

import { useCallback, useEffect, useState } from "react";

import { ApprovalPanel } from "@/components/ApprovalPanel";
import { CommentThread } from "@/components/CommentThread";
import { HighlightedText, type Mark } from "@/components/HighlightedText";
import { GROUPS, groupOf, HEX, TAG } from "@/components/severity";
import { StatusTimeline } from "@/components/StatusTimeline";
import { Button } from "@/components/ui/button";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type Finding, review, type ReviewDetail } from "@/lib/api";

const ACTION: Record<string, string> = {
  escalate: "asked a reviewer",
  uphold: "upheld",
  overrule: "overruled",
  accept: "accepted the fix",
  edit: "edited",
  dismiss: "dismissed",
};

function DecisionCard({
  n,
  f,
  group,
  detail,
  onDecide,
}: {
  n: number;
  f: Finding;
  group: (typeof GROUPS)[number];
  detail: ReviewDetail;
  onDecide: (action: "uphold" | "overrule", reason: string) => Promise<void>;
}) {
  const [pending, setPending] = useState<"uphold" | "overrule" | null>(null);
  const [reason, setReason] = useState("");
  const [sending, setSending] = useState(false);
  const history = detail.decisions.filter((d) => d.finding_id === f.record_id);
  const decided = [...history].reverse().find((d) => d.action === "uphold" || d.action === "overrule");
  const canDecide = Boolean(f.record_id && detail.can_decide.includes(f.record_id)) && detail.version.status !== "approved";
  return (
    <article id={`finding-${n}`} aria-label={`Finding ${n}: ${f.rule_id ?? f.fact_id ?? "finding"}`}
      className={`relative scroll-mt-24 overflow-hidden rounded-xl bg-panel p-4 pl-5 ring-1 ${decided ? "ring-ok/40" : "ring-line"}`}>
      <span aria-hidden className="absolute inset-y-0 left-0 w-1" style={{ background: HEX[group] }} />
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span aria-hidden className="inline-flex size-7 items-center justify-center rounded-full font-label text-sm font-bold text-ink" style={{ background: HEX[group] }}>{n}</span>
        <span className="sr-only">{n}</span>
        <span className={`rounded border px-2 py-0.5 font-label text-[11px] font-semibold uppercase ${TAG[group]}`}>{group}</span>
        {decided && (
          <span className="rounded border border-ok bg-ok/10 px-2 py-0.5 font-label text-[11px] font-semibold uppercase text-ok">
            ✓ {decided.action === "uphold" ? "Upheld" : "Overruled"}
          </span>
        )}
        <span className="ml-auto font-mono text-[11px] text-ash">{[f.rule_id, f.fact_id].filter(Boolean).join(" · ")}</span>
      </div>
      {f.quote && <p className="paper mt-3 rounded-md px-3 py-2 text-[15px] font-medium text-ink" style={{ boxShadow: `inset 0 -3px 0 ${HEX[group]}` }}>“{f.quote}”</p>}
      <p className="mt-3 leading-relaxed">{f.explanation}</p>
      {f.claim_status && <p className="mt-1 text-xs text-ash">Claim {f.claim_status.replace("_", " ")}</p>}
      <p className="mt-2 border-l border-line pl-3 text-xs text-ash">Source: {f.basis_excerpt}</p>
      {f.fix?.text && <p className="mt-3 rounded-lg border border-line bg-carbon/60 p-3 text-sm"><span className="font-label text-[11px] font-semibold uppercase text-ash">Suggested fix{f.fix.ref_id ? ` (${f.fix.ref_id})` : ""}: </span><b>{f.fix.text}</b></p>}
      {history.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-line pt-3 text-sm">
          {history.map((d, i) => (
            <li key={i}>
              <span className="font-medium">{d.who}</span> {ACTION[d.action] ?? d.action}
              {d.reason && <span className="text-muted-foreground">: “{d.reason}”</span>}
            </li>
          ))}
        </ul>
      )}
      {canDecide && !pending && (
        <div className="mt-3 flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setPending("uphold")}>Uphold</Button>
          <Button size="sm" variant="outline" onClick={() => setPending("overrule")}>Overrule</Button>
        </div>
      )}
      {pending && (
        <form className="mt-3 flex flex-wrap items-end gap-2 text-sm"
          onSubmit={async (e) => {
            e.preventDefault();
            setSending(true);
            try {
              await onDecide(pending, reason);
              setPending(null);
              setReason("");
            } finally {
              setSending(false);
            }
          }}>
          <label className="grow">
            Reason for {pending === "uphold" ? "upholding" : "overruling"} (required, goes in the audit log)
            <input className="mt-1 w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone focus:border-iris focus:outline-none" value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <Button size="sm" type="submit" disabled={sending || !reason.trim()}>
            {sending ? "Saving…" : `${pending === "uphold" ? "Uphold" : "Overrule"} with reason`}
          </Button>
          <Button size="sm" type="button" variant="ghost" onClick={() => setPending(null)}>Cancel</Button>
        </form>
      )}
    </article>
  );
}

export function ReviewVersion({ versionId }: { versionId: string }) {
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const [active, setActive] = useState<number | null>(null);
  const fail = (e: unknown) => setError(e instanceof CheckError ? e.message : "Something went wrong. Try again.");
  const act = useCallback(async (job: () => Promise<ReviewDetail>) => {
    setError(null);
    try {
      setDetail(await job());
    } catch (e) {
      fail(e);
    }
  }, []);
  useEffect(() => {
    review.get(versionId, setWaking).then(setDetail, fail);
  }, [versionId]);

  if (!detail) return <>{waking && <WakingBanner />}{error ? <p role="alert">{error}</p> : <p className="text-sm text-muted-foreground">Loading…</p>}</>;
  const rows = [
    ...detail.report.findings.map((f) => ({ f, group: groupOf(f, false) })),
    ...detail.report.needs_human.map((f) => ({ f, group: groupOf(f, true) })),
  ]
    .sort((a, b) => GROUPS.indexOf(a.group) - GROUPS.indexOf(b.group) || (a.f.span?.start ?? 1e9) - (b.f.span?.start ?? 1e9))
    .map((r, i) => ({ ...r, n: i + 1 }));
  const marks: Mark[] = rows.filter((r) => r.f.span).map((r) => ({ n: r.n, start: r.f.span!.start, end: r.f.span!.end, group: r.group }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-label text-xs font-semibold uppercase text-ash">
        <span className="font-display text-base tracking-normal normal-case text-bone">{detail.content.title}</span>
        <span>Version {detail.version.n}</span><span>{detail.content.origin}</span><span>{detail.content.channel}</span>
      </div>
      {error && <p role="alert" className="rounded-xl border border-blocking/40 bg-blocking/[0.07] px-4 py-3 text-sm text-blocking">{error}</p>}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-6">
          <section aria-label="Submitted text" className="paper rounded-xl">
            <p className="border-b border-ink/10 px-5 py-2.5 font-label text-[11px] font-semibold uppercase text-ink/70">Submitted text · version {detail.version.n}</p>
            <div className="px-5 py-4">
              <HighlightedText text={detail.report.checked_text ?? detail.version.text} marks={marks} active={active} onPick={setActive} />
            </div>
          </section>
          <ApprovalPanel
            detail={detail}
            onApprove={async () => {
              for (const stage of detail.can_approve) {
                const next = await review.approve(versionId, stage, "approve").catch((e) => (fail(e), null));
                if (!next) return;
                setDetail(next);
              }
            }}
            onRequestChanges={(reason) => act(() => review.approve(versionId, detail.can_approve[0], "request_changes", reason))}
          />
          <StatusTimeline events={detail.timeline} />
          <CommentThread comments={detail.comments} onAdd={(body) => act(() => review.comment(versionId, body))} />
        </div>
        <div className="min-w-0 space-y-3">
          <p className="font-display text-2xl font-bold uppercase tracking-[-0.01em]">
            <strong className="text-blocking">{rows.filter((r) => r.group === "Blocking").length} blocking</strong>{" "}
            <span className={detail.state.undecided_blocking.length ? "text-major" : "text-ok"}>· {detail.state.undecided_blocking.length} still to decide</span>
          </p>
          {rows.map((r) => (
            <DecisionCard key={r.f.id} n={r.n} f={r.f} group={r.group} detail={detail}
              onDecide={(action, reason) => act(() => review.decide(versionId, r.f.record_id!, action, reason))} />
          ))}
        </div>
      </div>
    </div>
  );
}
