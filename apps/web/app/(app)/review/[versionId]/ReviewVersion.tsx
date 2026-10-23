"use client";

import { useCallback, useEffect, useState } from "react";

import { ApprovalPanel } from "@/components/ApprovalPanel";
import { CommentThread } from "@/components/CommentThread";
import { HighlightedText, type Mark } from "@/components/HighlightedText";
import { GROUPS, groupOf, TAG } from "@/components/severity";
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
    <article aria-label={`Finding ${n}: ${f.rule_id ?? f.fact_id ?? "finding"}`} className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-semibold">{n}</span>
        <span className={`rounded border px-2 py-0.5 font-medium ${TAG[group]}`}>{group}</span>
        {decided && (
          <span className="rounded border border-ok bg-white px-2 py-0.5 font-medium text-ok">
            ✓ {decided.action === "uphold" ? "Upheld" : "Overruled"}
          </span>
        )}
        <span className="font-mono text-xs">{[f.rule_id, f.fact_id].filter(Boolean).join(" · ")}</span>
        {f.claim_status && <span className="text-muted-foreground">claim {f.claim_status.replace("_", " ")}</span>}
      </div>
      {f.quote && <p className="mt-2 font-medium">“{f.quote}”</p>}
      <p className="mt-1">{f.explanation}</p>
      <p className="mt-1 text-xs text-muted-foreground">Source: {f.basis_excerpt}</p>
      {f.fix?.text && <p className="mt-2 text-sm">Suggested fix{f.fix.ref_id ? ` (${f.fix.ref_id})` : ""}: {f.fix.text}</p>}
      {history.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm">
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
            <input className="mt-1 w-full rounded border px-2 py-1" value={reason} onChange={(e) => setReason(e.target.value)} />
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
      <p className="text-sm text-muted-foreground">
        {detail.content.title} · version {detail.version.n} · {detail.content.origin} · {detail.content.channel}
      </p>
      {error && <p role="alert" className="rounded-lg border border-blocking/40 bg-white px-4 py-3 text-sm text-blocking">{error}</p>}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-6">
          <section aria-label="Submitted text" className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
            <HighlightedText text={detail.report.checked_text ?? detail.version.text} marks={marks} />
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
          <p className="text-lg">
            <strong>{rows.filter((r) => r.group === "Blocking").length} blocking</strong> ·{" "}
            {detail.state.undecided_blocking.length} still to decide
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
