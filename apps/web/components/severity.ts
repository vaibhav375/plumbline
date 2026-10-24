import type { Finding } from "@/lib/api";

export type Group = "Blocking" | "Major" | "Minor" | "Needs human eyes" | "Advisory";
export const GROUPS: Group[] = ["Blocking", "Major", "Minor", "Needs human eyes", "Advisory"];

// Colour always comes with a word (and a number), never on its own. Tags sit on the dark panels in
// the bright severity colours (each >= 6.3:1 there); marks on the paper sheet keep ink text, with the
// colour only in the underline and the pin.
const DOT = "before:mr-1.5 before:inline-block before:size-2 before:rounded-full before:bg-current before:content-['']";

/** Labelled tags: group chips and box numbers. */
export const TAG: Record<Group, string> = {
  Blocking: `border-blocking/70 bg-blocking/10 text-blocking ${DOT}`,
  Major: `border-major/70 bg-major/10 text-major ${DOT}`,
  Minor: `border-minor/70 bg-minor/10 text-minor ${DOT}`,
  "Needs human eyes": `border-iris/70 bg-iris/10 text-iris ${DOT}`,
  Advisory: `border-line bg-white/5 text-ash ${DOT}`,
};

/** The same colours as hex, for inline styles (underlines, pins, chart marks). */
export const HEX: Record<Group, string> = {
  Blocking: "#FF6A5C",
  Major: "#F0A03C",
  Minor: "#74A7F0",
  "Needs human eyes": "#A39CFF",
  Advisory: "#9B9AA1",
};

/** Outlines drawn on images. */
export const EDGE: Record<Group, string> = {
  Blocking: "border-blocking",
  Major: "border-major",
  Minor: "border-minor",
  "Needs human eyes": "border-iris",
  Advisory: "border-ash",
};

export function groupOf(f: Finding, needsHuman: boolean): Group {
  if (needsHuman) return "Needs human eyes";
  if (f.advisory) return "Advisory";
  return f.severity === "blocking" ? "Blocking" : f.severity === "major" ? "Major" : "Minor";
}
