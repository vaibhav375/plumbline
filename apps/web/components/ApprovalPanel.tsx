"use client";

import { useState } from "react";

import { StagePipeline } from "@/components/StagePipeline";
import { Button } from "@/components/ui/button";
import type { ReviewDetail } from "@/lib/api";

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
    <section aria-labelledby="approvals" className="rounded-xl border border-line bg-panel p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="approvals" className="text-base">Approvals</h2>
        <p className={`font-label text-xs font-semibold uppercase ${done ? "text-ok" : "text-major"}`} data-testid="version-status">Status: {detail.version.status.replace("_", " ")}</p>
      </div>
      <div className="mt-4 overflow-x-auto pb-1">
        <StagePipeline required={state.required} approved={state.approved} />
      </div>
      <p className="mt-3 text-xs text-ash">Compliance signs off claims and confidential details; an overruled blocking finding needs a second, different approver.</p>
      {!done && (
        <div className="mt-4 flex flex-wrap gap-2">
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
            <input className="mt-1 w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone focus:border-iris focus:outline-none" value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <Button size="sm" type="submit" disabled={!reason.trim()}>Send back</Button>
        </form>
      )}
    </section>
  );
}
