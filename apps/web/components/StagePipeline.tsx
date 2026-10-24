import { Check } from "lucide-react";

const SHORT: Record<string, string> = { first: "Review", compliance: "Compliance", accessibility: "Accessibility", second: "Second approver" };

/** The approval stages a version needs, in order, as a pipeline: filled once approved. */
export function StagePipeline({ required, approved, compact = false }: { required: string[]; approved: string[]; compact?: boolean }) {
  return (
    <ol aria-label="Approval stages" className="flex items-center">
      {required.map((s, i) => {
        const done = approved.includes(s);
        return (
          <li key={s} className="flex items-center">
            {i > 0 && <span aria-hidden className={`h-0.5 ${compact ? "w-4" : "w-8"} ${done ? "bg-ok" : "bg-line"}`} />}
            <span className="flex items-center gap-1.5">
              <span aria-hidden className={`inline-flex ${compact ? "size-5" : "size-7"} items-center justify-center rounded-full border-[1.5px] ${done ? "border-ok bg-ok text-ink" : "border-ash/60 text-ash"}`}>
                {done ? <Check className={compact ? "size-3" : "size-4"} /> : <span className="font-label text-[10px] font-bold">{i + 1}</span>}
              </span>
              <span className={`font-label ${compact ? "text-[11px]" : "text-xs"} font-semibold uppercase tracking-[0.12em] ${done ? "text-ok" : "text-bone/80"}`}>
                {SHORT[s] ?? s}<span className="sr-only">{done ? ": approved" : ": waiting"}</span>
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
