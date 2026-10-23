import { wordDiff } from "@/lib/diff";

export function DiffView({ before, after }: { before: string; after: string }) {
  return (
    <section aria-label="Changes" className="rounded-xl bg-white shadow-sm ring-1 ring-ink/5 p-4">
      <h2 className="font-semibold">Changes from the previous version</h2>
      <p className="mt-2 whitespace-pre-wrap leading-7">
        {wordDiff(before, after).map((p, i) =>
          p.kind === "same" ? <span key={i}>{p.text}</span>
            : p.kind === "add" ? <ins key={i} className="bg-green-100 text-green-900 no-underline">{p.text}</ins>
              : <del key={i} className="bg-red-100 text-red-900">{p.text}</del>,
        )}
      </p>
    </section>
  );
}
