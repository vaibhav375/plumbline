import { AlertOctagon, AlertTriangle, Eye, Info, Lightbulb } from "lucide-react";

import type { Group } from "@/components/severity";

// One tile per group, each labelled: severity is told by words and icons, not colour alone
// (blocking red and major amber are too close for red-green colour blindness).
const META: Record<Group, { icon: typeof Info; color: string; hint: string }> = {
  Blocking: { icon: AlertOctagon, color: "#C2362B", hint: "Must be fixed before publishing" },
  Major: { icon: AlertTriangle, color: "#A86400", hint: "Should be fixed" },
  Minor: { icon: Info, color: "#3D6FB6", hint: "Worth fixing" },
  "Needs human eyes": { icon: Eye, color: "#4B3FD1", hint: "A person should decide" },
  Advisory: { icon: Lightbulb, color: "#64748B", hint: "Suggestions; never block" },
};

export function SeverityTiles({ counts }: { counts: Record<Group, number> }) {
  const total = Math.max(1, Object.values(counts).reduce((a, b) => a + b, 0));
  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="Findings by severity">
      {(Object.keys(META) as Group[]).map((g) => {
        const { icon: Icon, color, hint } = META[g];
        return (
          <li key={g} title={`${counts[g]} ${g.toLowerCase()}: ${hint}`} className="rounded-lg bg-white p-2.5 ring-1 ring-ink/5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-ink">
              <Icon className="size-3.5 shrink-0" style={{ color }} aria-hidden />
              {g}
            </div>
            <p className="mt-1 font-display text-2xl font-bold tabular-nums text-ink">{counts[g]}</p>
            <div className="mt-1 h-1.5 rounded-full bg-chalk" aria-hidden>
              <div className="h-1.5 rounded-full" style={{ width: `${(counts[g] / total) * 100}%`, background: color, minWidth: counts[g] ? 6 : 0 }} />
            </div>
            <p className="mt-1 text-[11px] leading-tight text-muted-foreground">{hint}</p>
          </li>
        );
      })}
    </ul>
  );
}
