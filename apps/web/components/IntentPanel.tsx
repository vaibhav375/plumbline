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
    <section aria-labelledby="intent" className="rounded-lg border p-4">
      <h2 id="intent" className="font-semibold">Intent lock on the suggested version</h2>
      <ul className="mt-2 space-y-1 text-sm">
        {CHECKS.map(([key, label]) => (
          <li key={key}>
            <span aria-hidden>{intent[key] ? "✓" : "✗"}</span> {label}
            <span className="sr-only">{intent[key] ? ": kept" : ": not kept"}</span>
          </li>
        ))}
      </ul>
      {suggested && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">Suggested version (intent kept, no invented claims)</summary>
          <p className="mt-2 whitespace-pre-wrap">{suggested}</p>
        </details>
      )}
    </section>
  );
}
