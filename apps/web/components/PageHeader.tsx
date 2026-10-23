/** A page's title and, in plain words, what the page is for. */
export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="space-y-1 pb-2">
      <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">{title}</h1>
      <p className="max-w-3xl text-muted-foreground">{subtitle}</p>
    </header>
  );
}
