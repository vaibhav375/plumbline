/** Shown the instant you click: the page frame, while its data loads. */
export default function Loading() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6" aria-busy="true" aria-label="Loading">
      <div className="space-y-2">
        <div className="h-9 w-64 animate-pulse rounded-md bg-ink/10" />
        <div className="h-4 w-96 max-w-full animate-pulse rounded bg-ink/10" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-40 animate-pulse rounded-xl bg-white shadow-sm ring-1 ring-ink/5" />
        <div className="h-40 animate-pulse rounded-xl bg-white shadow-sm ring-1 ring-ink/5" />
      </div>
      <p className="text-sm text-muted-foreground">Loading…</p>
    </main>
  );
}
