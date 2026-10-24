import type { CheckReport } from "@/lib/api";

const CHECKS: [keyof NonNullable<CheckReport["intent"]>, string][] = [
  ["cta_kept", "Call to action kept"],
  ["pinned_phrases_kept", "Pinned phrases kept"],
  ["no_claim_dropped", "No claim dropped silently"],
  ["channel_limits_ok", "Within the channel's length limit"],
  ["edits_in_flagged_sentences", "Edits stay inside flagged sentences"],
];

export function IntentPanel({ intent, suggested }: { intent: CheckReport["intent"]; suggested?: string | null }) {
  if (!intent) return null;
  return (
    <section aria-labelledby="intent" className="rounded-xl bg-panel p-5 ring-1 ring-line">
      <h2 id="intent" className="text-base">Does the suggested version keep your message?</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {CHECKS.map(([key, label]) => (
          <li key={key} className="flex items-center gap-2">
            <span aria-hidden className={`inline-flex size-5 items-center justify-center rounded-full text-xs font-bold text-ink ${intent[key] ? "bg-ok" : "bg-blocking"}`}>{intent[key] ? "✓" : "✗"}</span> {label}
            <span className="sr-only">{intent[key] ? ": kept" : ": not kept"}</span>
          </li>
        ))}
      </ul>
      {suggested && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">Suggested version (intent kept, no invented claims)</summary>
          <p className="paper mt-2 whitespace-pre-wrap rounded-md p-3 text-ink">{suggested}</p>
        </details>
      )}
    </section>
  );
}
