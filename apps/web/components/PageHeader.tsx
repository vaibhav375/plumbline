/** A page's title and, in plain words, what the page is for, over the drafting texture. */
export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="relative -mx-4 -mt-4 mb-2 overflow-hidden border-b border-line bg-panel px-4 pt-8 pb-6 sm:-mx-6 sm:-mt-6 sm:px-6 sm:pt-10">
      <div aria-hidden className="guides contours pointer-events-none absolute inset-0 opacity-70" />
      <div className="relative space-y-2">
        <p className="font-label text-xs font-semibold uppercase tracking-[0.18em] text-bone/55">Plumbline · Aurelle Skin</p>
        <h1 className="font-display text-4xl font-extrabold uppercase leading-[0.92] tracking-[-0.025em] text-bone sm:text-6xl">{title}</h1>
        <p className="max-w-3xl text-[15px] text-bone/70">{subtitle}</p>
      </div>
    </header>
  );
}
