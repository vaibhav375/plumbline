import type { ReviewDetail } from "@/lib/api";

export function StatusTimeline({ events }: { events: ReviewDetail["timeline"] }) {
  return (
    <section aria-labelledby="timeline" className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
      <h2 id="timeline" className="font-semibold">Timeline</h2>
      <ol className="mt-2 space-y-2 text-sm">
        {events.map((e, i) => (
          <li key={i}>
            <time className="text-muted-foreground" dateTime={e.at}>
              {new Date(e.at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
            </time>{" "}
            · <span className="font-medium">{e.who}</span> {e.what}
            {e.reason && <span className="text-muted-foreground">: “{e.reason}”</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
