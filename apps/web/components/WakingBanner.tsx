export function WakingBanner() {
  return (
    <div role="status" aria-live="polite" className="rounded-md border border-major/50 bg-major/10 px-4 py-3 text-sm text-major">
      Waking the checker (free hosting sleeps when idle). About 30 seconds.
    </div>
  );
}
