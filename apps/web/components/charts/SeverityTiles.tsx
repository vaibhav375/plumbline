import { AlertOctagon, AlertTriangle, Eye, Info, Lightbulb } from "lucide-react";

import type { Group } from "@/components/severity";

// One tile per group, each labelled: severity is told by words and icons, not colour alone
// (blocking red and major amber are too close for red-green colour blindness).
const META: Record<Group, { icon: typeof Info; color: string; hint: string }> = {
  Blocking: { icon: AlertOctagon, color: "#FF6A5C", hint: "Must be fixed before publishing" },
  Major: { icon: AlertTriangle, color: "#F0A03C", hint: "Should be fixed" },
  Minor: { icon: Info, color: "#74A7F0", hint: "Worth fixing" },
  "Needs human eyes": { icon: Eye, color: "#A39CFF", hint: "A person should decide" },
  Advisory: { icon: Lightbulb, color: "#9B9AA1", hint: "Suggestions; never block" },
};

export function SeverityTiles({ counts }: { counts: Record<Group, number> }) {
  const total = Math.max(1, Object.values(counts).reduce((a, b) => a + b, 0));
  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="Findings by severity">
      {(Object.keys(META) as Group[]).map((g) => {
        const { icon: Icon, color, hint } = META[g];
        return (
          <li key={g} title={`${counts[g]} ${g.toLowerCase()}: ${hint}`} className="rounded-lg bg-panel p-2.5 ring-1 ring-line">
            <div className="flex items-center gap-1.5 text-xs font-medium text-bone">
              <Icon className="size-3.5 shrink-0" style={{ color }} aria-hidden />
              {g}
            </div>
            <p className="mt-1 font-display text-2xl font-bold tabular-nums text-bone">{counts[g]}</p>
            <div className="mt-1 h-1.5 rounded-full bg-raised" aria-hidden>
              <div className="h-1.5 rounded-full" style={{ width: `${(counts[g] / total) * 100}%`, background: color, minWidth: counts[g] ? 6 : 0 }} />
            </div>
            <p className="mt-1 text-[11px] leading-tight text-muted-foreground">{hint}</p>
          </li>
        );
      })}
    </ul>
  );
}
