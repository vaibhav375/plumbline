import type { ReviewDetail } from "@/lib/api";

export function StatusTimeline({ events }: { events: ReviewDetail["timeline"] }) {
  return (
    <section aria-labelledby="timeline" className="rounded-xl border border-line bg-panel p-5">
      <h2 id="timeline" className="text-base">Timeline</h2>
      <ol className="mt-4 space-y-4 border-l border-line pl-5 text-sm">
        {events.map((e, i) => (
          <li key={i} className="relative">
            <span aria-hidden className={`absolute top-1.5 -left-[25px] size-2.5 rounded-full ring-4 ring-panel ${i === events.length - 1 ? "bg-iris" : "bg-ash"}`} />
            <time className="block font-label text-[11px] font-semibold uppercase text-ash" dateTime={e.at}>
              {new Date(e.at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" })}
            </time>
            <span className="font-medium text-bone">{e.who}</span> {e.what}
            {e.reason && <span className="text-muted-foreground">: “{e.reason}”</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
