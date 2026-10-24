import { wordDiff } from "@/lib/diff";

export function DiffView({ before, after }: { before: string; after: string }) {
  return (
    <section aria-label="Changes" className="paper rounded-xl p-5">
      <h2 className="text-base text-ink">Changes from the previous version</h2>
      <p className="mt-2 whitespace-pre-wrap leading-8 text-ink">
        {wordDiff(before, after).map((p, i) =>
          p.kind === "same" ? <span key={i}>{p.text}</span>
            : p.kind === "add" ? <ins key={i} className="rounded-sm bg-[#1E7F55]/15 px-0.5 font-semibold text-ink no-underline ring-1 ring-[#1E7F55]/50">{p.text}</ins>
              : <del key={i} className="text-ink/50 decoration-[#C2362B] decoration-2">{p.text}</del>,
        )}
      </p>
    </section>
  );
}
