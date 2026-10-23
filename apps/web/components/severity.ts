import type { Finding } from "@/lib/api";

export type Group = "Blocking" | "Major" | "Minor" | "Needs human eyes" | "Advisory";
export const GROUPS: Group[] = ["Blocking", "Major", "Minor", "Needs human eyes", "Advisory"];

// Colour always comes with a word (and a number), never on its own. Tags are white with a coloured
// border, dot and text (every colour is >= 4.68:1 on white); highlights keep ink text on a light
// tint, because the brand colours drop below 4.5:1 on their own tints.
const DOT = "before:mr-1.5 before:inline-block before:size-2 before:rounded-full before:bg-current before:content-['']";

/** Labelled tags: group chips and box numbers. */
export const TAG: Record<Group, string> = {
  Blocking: `border-blocking bg-white text-blocking ${DOT}`,
  Major: `border-major bg-white text-major ${DOT}`,
  Minor: `border-minor bg-white text-minor ${DOT}`,
  "Needs human eyes": `border-accent-brand bg-white text-accent-brand ${DOT}`,
  Advisory: `border-slate-400 bg-white text-slate-700 ${DOT}`,
};

/** Highlights in the draft. */
export const MARK: Record<Group, string> = {
  Blocking: "border-blocking bg-blocking/10 text-ink",
  Major: "border-major bg-major/10 text-ink",
  Minor: "border-minor bg-minor/10 text-ink",
  "Needs human eyes": "border-accent-brand bg-accent-brand/10 text-ink",
  Advisory: "border-slate-400 bg-slate-100 text-ink",
};

/** Outlines drawn on images. */
export const EDGE: Record<Group, string> = {
  Blocking: "border-blocking",
  Major: "border-major",
  Minor: "border-minor",
  "Needs human eyes": "border-accent-brand",
  Advisory: "border-slate-400",
};

export function groupOf(f: Finding, needsHuman: boolean): Group {
  if (needsHuman) return "Needs human eyes";
  if (f.advisory) return "Advisory";
  return f.severity === "blocking" ? "Blocking" : f.severity === "major" ? "Major" : "Minor";
}
