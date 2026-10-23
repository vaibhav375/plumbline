import { MARK, type Group } from "@/components/severity";
import { utf16Index } from "@/lib/offsets";

// `replacement` is set once a fix is accepted or the text edited: "" means the words are removed.
export type Mark = { n: number; start: number; end: number; group: Group; replacement?: string };

/** The draft with each finding's quote marked: colour plus a numbered superscript. */
export function HighlightedText({ text, marks }: { text: string; marks: Mark[] }) {
  const spans = marks
    .map((m) => ({ ...m, s: utf16Index(text, m.start), e: utf16Index(text, m.end) }))
    .filter((m) => m.e > m.s)
    .sort((a, b) => a.s - b.s || b.e - a.e);
  const parts: React.ReactNode[] = [];
  let pos = 0;
  for (const m of spans) {
    if (m.s < pos) {
      // Overlapping finding: number it where the earlier highlight already covers the words.
      parts.push(<sup key={`o${m.n}`} className="ml-0.5 font-semibold">{m.n}</sup>);
      continue;
    }
    if (m.s > pos) parts.push(text.slice(pos, m.s));
    parts.push(
      m.replacement !== undefined ? (
        <span key={m.n} className="change-in" aria-label={`Finding ${m.n}: will change`}>
          <del className="text-ink/45 decoration-blocking decoration-2">{text.slice(m.s, m.e)}</del>{" "}
          {m.replacement ? (
            <ins className="rounded bg-ok/12 px-1 font-semibold text-ok no-underline ring-1 ring-ok/40">{m.replacement}</ins>
          ) : (
            <ins className="font-label text-xs font-semibold uppercase tracking-wide text-ok no-underline">removed</ins>
          )}
          <sup className="ml-0.5 font-semibold">{m.n}</sup>
        </span>
      ) : (
        <mark key={m.n} className={`rounded border px-0.5 ${MARK[m.group]}`} aria-label={`Finding ${m.n}: ${m.group}`}>
          {text.slice(m.s, m.e)}
          <sup className="ml-0.5 font-semibold">{m.n}</sup>
        </mark>
      ),
    );
    pos = m.e;
  }
  parts.push(text.slice(pos));
  return <p className="whitespace-pre-wrap leading-8">{parts}</p>;
}
