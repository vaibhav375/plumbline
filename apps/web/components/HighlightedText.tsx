import { MARK, type Group } from "@/components/severity";
import { utf16Index } from "@/lib/offsets";

export type Mark = { n: number; start: number; end: number; group: Group };

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
      <mark key={m.n} className={`rounded border px-0.5 ${MARK[m.group]}`} aria-label={`Finding ${m.n}: ${m.group}`}>
        {text.slice(m.s, m.e)}
        <sup className="ml-0.5 font-semibold">{m.n}</sup>
      </mark>,
    );
    pos = m.e;
  }
  parts.push(text.slice(pos));
  return <p className="whitespace-pre-wrap leading-8">{parts}</p>;
}
