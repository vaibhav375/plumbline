export function WakingBanner() {
  return (
    <div role="status" aria-live="polite" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      Waking the checker (free hosting sleeps when idle). About 30 seconds.
    </div>
  );
}
