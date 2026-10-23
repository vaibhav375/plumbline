"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { ReviewDetail } from "@/lib/api";

const STAGE: Record<string, string> = {
  first: "Review",
  compliance: "Compliance (claims and confidential)",
  accessibility: "Accessibility",
  second: "Second approver (a different person)",
};

export function ApprovalPanel({
  detail,
  onApprove,
  onRequestChanges,
}: {
  detail: ReviewDetail;
  onApprove: () => Promise<void>;
  onRequestChanges: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState<string | null>(null);
  const { state, can_approve } = detail;
  const undecided = state.undecided_blocking.length;
  const done = detail.version.status === "approved";
  return (
    <section aria-labelledby="approvals" className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
      <h2 id="approvals" className="font-semibold">Approvals</h2>
      <p className="mt-1 text-sm" data-testid="version-status">Status: {detail.version.status.replace("_", " ")}</p>
      <ul className="mt-2 space-y-1 text-sm">
        {state.required.map((s) => (
          <li key={s}>
            <span aria-hidden>{state.approved.includes(s) ? "✓" : "○"}</span> {STAGE[s] ?? s}
            <span className="sr-only">{state.approved.includes(s) ? ": approved" : ": waiting"}</span>
          </li>
        ))}
      </ul>
      {!done && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button disabled={!can_approve.length || undecided > 0} onClick={onApprove}
            title={undecided ? "Decide every blocking finding first." : !can_approve.length ? "Your role has no approval left here." : undefined}>
            {undecided ? `Approve (${undecided} blocking to decide)` : "Approve"}
          </Button>
          <Button variant="outline" disabled={!can_approve.length} onClick={() => setReason("")}>Request changes</Button>
        </div>
      )}
      {reason !== null && (
        <form className="mt-3 flex flex-wrap items-end gap-2 text-sm"
          onSubmit={async (e) => { e.preventDefault(); await onRequestChanges(reason); setReason(null); }}>
          <label className="grow">
            What needs to change? (required)
            <input className="mt-1 w-full rounded border px-2 py-1" value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <Button size="sm" type="submit" disabled={!reason.trim()}>Send back</Button>
        </form>
      )}
    </section>
  );
}
