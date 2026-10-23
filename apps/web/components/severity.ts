import type { Finding } from "@/lib/api";

export type Group = "Blocking" | "Major" | "Minor" | "Needs human eyes" | "Advisory";
export const GROUPS: Group[] = ["Blocking", "Major", "Minor", "Needs human eyes", "Advisory"];

/** Colour always comes with a word and a number, never on its own. */
export const TONE: Record<Group, string> = {
  Blocking: "border-red-300 bg-red-50 text-red-900",
  Major: "border-amber-300 bg-amber-50 text-amber-900",
  Minor: "border-slate-300 bg-slate-50 text-slate-800",
  "Needs human eyes": "border-violet-300 bg-violet-50 text-violet-900",
  Advisory: "border-slate-200 bg-white text-slate-700",
};

export function groupOf(f: Finding, needsHuman: boolean): Group {
  if (needsHuman) return "Needs human eyes";
  if (f.advisory) return "Advisory";
  return f.severity === "blocking" ? "Blocking" : f.severity === "major" ? "Major" : "Minor";
}
