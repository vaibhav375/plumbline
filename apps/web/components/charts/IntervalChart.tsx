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
// Label | track | values. The track's inner box is inset so a dot at 0% or 100% isn't clipped.
const GRID = "grid grid-cols-[34%_1fr_3.75rem] sm:grid-cols-[28%_1fr_3.75rem]";
const INNER = "absolute inset-y-0 inset-x-2";

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
      <div>
        {/* The threshold label sits in its own row, on the same scale as the tracks below. */}
        {threshold && (
          <div className={GRID} aria-hidden>
            <span />
            <div className="relative h-7">
              <div className={INNER}>
                <span className="absolute bottom-1 -translate-x-1/2 whitespace-nowrap font-label text-xs font-semibold uppercase tracking-wide text-ink"
                  style={{ left: pct(threshold.value) }}>
                  {threshold.label}
                </span>
              </div>
            </div>
            <span />
          </div>
        )}
        <ul>
          {rows.map((r) => (
            <li key={r.label} className={`${GRID} items-center`}>
              <div className="py-1.5 pr-3 text-sm">
                <span className="font-mono text-xs font-medium">{r.label}</span>
                {r.sub && <span className="block truncate text-xs text-muted-foreground">{r.sub}</span>}
              </div>
              <div className="relative h-12 border-b border-dashed border-ink/15">
                <div className={INNER}>
                  {threshold && (
                    <span aria-hidden className="absolute inset-y-0 z-10 w-0.5 -translate-x-1/2 bg-ink" style={{ left: pct(threshold.value) }} />
                  )}
                  {r.points.map((p, i) => {
                    const s = series[i];
                    const y = r.points.length > 1 ? `${32 + i * 36}%` : "50%";
                    return (
                      <div key={s.name} title={p.tip} className="group absolute inset-x-0 z-20 h-5 -translate-y-1/2 cursor-default" style={{ top: y }}>
                        <span className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full opacity-70"
                          style={{ left: pct(p.lo), width: `calc(${pct(p.hi)} - ${pct(p.lo)})`, background: s.color }} />
                        <span className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white transition-transform duration-300 group-hover:scale-150"
                          style={{ left: pct(p.value), background: s.color }} />
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="flex flex-col justify-center gap-1 pl-3 text-xs font-semibold leading-tight tabular-nums text-ink">
                {r.points.map((p, i) => <span key={series[i].name}>{p.label}</span>)}
              </div>
            </li>
          ))}
        </ul>
        <div className={GRID} aria-hidden>
          <span />
          <div className="relative h-6">
            <div className={`${INNER} text-[11px] text-muted-foreground`}>
              {threshold && (
                <svg viewBox="0 0 10 12" className="absolute -top-px size-2.5 -translate-x-1/2" style={{ left: pct(threshold.value) }}>
                  <path d="M5 0 L10 6 L5 12 L0 6 Z" fill="#0A0A0A" />
                </svg>
              )}
              {[0, 0.5, 1].map((t) => (
                <span key={t} className="absolute top-2 -translate-x-1/2" style={{ left: pct(t) }}>{Math.round(t * 100)}%</span>
              ))}
            </div>
          </div>
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
