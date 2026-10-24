"use client";

import { AnimatePresence, motion } from "motion/react";
import { Fragment } from "react";

import { type Group, HEX as EDGE } from "@/components/severity";
import { utf16Index } from "@/lib/offsets";

// `replacement` is set once a fix is accepted or the text edited: "" means the words are removed.
export type Mark = { n: number; start: number; end: number; group: Group; replacement?: string };


function Pin({ n, group, active }: { n: number; group: Group; active: boolean }) {
  return (
    <span aria-hidden
      className={`mr-1 inline-flex size-[1.15rem] -translate-y-[0.12em] items-center justify-center rounded-full align-middle font-label text-[10px] font-bold text-ink transition-transform duration-200 ${active ? "scale-125" : ""}`}
      style={{ background: EDGE[group] }}>
      {n}
    </span>
  );
}

/** The post as a sheet of paper: each finding underlined in its severity colour with a numbered pin.
 * Hovering a finding (or a mark) lights it up; an accepted change is struck through and replaced. */
export function HighlightedText({ text, marks, active = null, onPick }: {
  text: string;
  marks: Mark[];
  active?: number | null;
  onPick?: (n: number) => void;
}) {
  const spans = marks
    .map((m) => ({ ...m, s: utf16Index(text, m.start), e: utf16Index(text, m.end) }))
    .filter((m) => m.e > m.s)
    .sort((a, b) => a.s - b.s || b.e - a.e);
  const parts: React.ReactNode[] = [];
  let pos = 0;
  for (const m of spans) {
    if (m.s < pos) {
      // Overlapping finding: pin it where the earlier highlight already covers the words.
      parts.push(<Pin key={`o${m.n}`} n={m.n} group={m.group} active={active === m.n} />);
      continue;
    }
    if (m.s > pos) parts.push(text.slice(pos, m.s));
    const isActive = active === m.n;
    parts.push(
      m.replacement !== undefined ? (
        <span key={m.n} aria-label={`Finding ${m.n}: will change`} className="relative">
          <Pin n={m.n} group={m.group} active={isActive} />
          <motion.del initial={{ opacity: 1 }} animate={{ opacity: 0.45 }} transition={{ duration: 0.4 }}
            className="decoration-[#C2362B] decoration-2">{text.slice(m.s, m.e)}</motion.del>{" "}
          <AnimatePresence>
            <motion.ins key="ins" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 380, damping: 26 }}
              className={`rounded px-1 font-semibold no-underline ${m.replacement ? "bg-[#1E7F55]/15 text-ink ring-1 ring-[#1E7F55]/50" : "font-label text-xs uppercase tracking-wide text-[#1E7F55]"}`}>
              {m.replacement || "removed"}
            </motion.ins>
          </AnimatePresence>
        </span>
      ) : (
        <Fragment key={m.n}>
        {/* The pin sits just outside the mark, so the mark holds exactly the flagged words. */}
        <Pin n={m.n} group={m.group} active={isActive} />
        <mark aria-label={`Finding ${m.n}: ${m.group}`} onMouseEnter={() => onPick?.(m.n)}
          onClick={() => {
            onPick?.(m.n);
            document.getElementById(`finding-${m.n}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
          }}
          className="cursor-pointer rounded-sm px-0.5 text-ink transition-colors duration-200"
          style={{
            background: isActive ? `${EDGE[m.group]}55` : `${EDGE[m.group]}1f`,
            boxShadow: `inset 0 -3px 0 ${EDGE[m.group]}`,
          }}>
          {text.slice(m.s, m.e)}
        </mark>
        </Fragment>
      ),
    );
    pos = m.e;
  }
  parts.push(text.slice(pos));
  return <p className="whitespace-pre-wrap text-[17px] leading-[2.1rem] text-ink">{parts}</p>;
}
