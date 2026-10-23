/**
 * Point estimates with 95% intervals on a 0–100% scale, measured against a vertical threshold:
 * the plumb line. HTML positioned in percentages, so it scales with its container.
 * Identity is never colour alone: two series get a legend and direct labels; every mark has a
 * hover tooltip; callers provide a table with the same numbers.
 */
export type Series = { name: string; color: string };
export type Point = { value: number; lo: number; hi: number; label: string; tip: string };
export type Row = { label: string; sub?: string; points: Point[] };

const pct = (x: number) => `${Math.max(0, Math.min(100, x * 100))}%`;

export function IntervalChart({
  rows,
  series,
  threshold,
  caption,
}: {
  rows: Row[];
  series: Series[];
  threshold?: { value: number; label: string };
  caption: string;
}) {
  return (
    <figure className="space-y-3">
      {series.length > 1 && (
        <ul className="flex flex-wrap gap-4 text-sm" aria-label="Legend">
          {series.map((s) => (
            <li key={s.name} className="flex items-center gap-2">
              <span className="inline-block size-3 rounded-full" style={{ background: s.color }} aria-hidden />
              {s.name}
            </li>
          ))}
        </ul>
      )}
      <div className="relative">
        {threshold && (
          <div className="pointer-events-none absolute inset-y-0 right-14 left-[34%] sm:left-[28%]" aria-hidden>
            <div className="absolute inset-y-0 -translate-x-px border-l-2 border-ink" style={{ left: pct(threshold.value) }}>
              <span className="absolute -top-5 left-1 whitespace-nowrap text-[11px] font-semibold text-ink">{threshold.label}</span>
              <svg viewBox="0 0 10 12" className="absolute -bottom-3 -left-[6px] size-2.5"><path d="M5 0 L10 6 L5 12 L0 6 Z" fill="#141B2D" /></svg>
            </div>
          </div>
        )}
        <ul className="space-y-1 pt-5">
          {rows.map((r) => (
            <li key={r.label} className="grid grid-cols-[34%_1fr_3.5rem] items-center gap-0 sm:grid-cols-[28%_1fr_3.5rem]">
              <div className="pr-3 text-sm">
                <span className="font-mono text-xs font-medium">{r.label}</span>
                {r.sub && <span className="block truncate text-xs text-muted-foreground">{r.sub}</span>}
              </div>
              <div className="relative h-10 rounded-md bg-chalk">
                {r.points.map((p, i) => {
                  const s = series[i];
                  const y = r.points.length > 1 ? `${30 + i * 40}%` : "50%";
                  return (
                    <div key={s.name} title={p.tip} className="group absolute inset-x-0 h-4 -translate-y-1/2 cursor-default" style={{ top: y }}>
                      <span className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full opacity-60"
                        style={{ left: pct(p.lo), width: `calc(${pct(p.hi)} - ${pct(p.lo)})`, background: s.color }} />
                      <span className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white transition-transform group-hover:scale-125"
                        style={{ left: pct(p.value), background: s.color }} />
                    </div>
                  );
                })}
              </div>
              <div className="flex flex-col justify-center gap-0.5 pl-2 text-[11px] font-medium leading-tight tabular-nums text-ink">
                {r.points.map((p, i) => <span key={series[i].name}>{p.label}</span>)}
              </div>
            </li>
          ))}
        </ul>
        <div className="grid grid-cols-[34%_1fr_3.5rem] pt-1 text-[11px] text-muted-foreground sm:grid-cols-[28%_1fr_3.5rem]" aria-hidden>
          <span />
          <div className="flex justify-between"><span>0%</span><span>50%</span><span>100%</span></div>
          <span />
        </div>
      </div>
      <figcaption className="text-xs text-muted-foreground">{caption}</figcaption>
    </figure>
  );
}

/** 95% Wilson score interval, the same formula as the checker's (plumbline/health.py). */
export function wilson(k: number, n: number): [number, number] {
  if (n === 0) return [0, 1];
  const z = 1.96, p = k / n;
  const lower = (x: number) =>
    (x + (z * z) / (2 * n) - z * Math.sqrt((x * (1 - x)) / n + (z * z) / (4 * n * n))) / (1 + (z * z) / n);
  return [Math.max(0, lower(p)), Math.min(1, 1 - lower(1 - p))];
}
