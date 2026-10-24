"use client";

import { useEffect, useState } from "react";

import { rulebook } from "@/lib/api";

// One request per visit: every finding card reads the same map. A failure leaves cards with just the code.
let pending: Promise<Record<string, string>> | null = null;

/** The plain-English title of a rule (e.g. "At most one exclamation mark" for TN-02), once loaded. */
export function useRuleTitle(id: string | null | undefined): string | undefined {
  const [titles, setTitles] = useState<Record<string, string>>({});
  useEffect(() => {
    pending ??= rulebook
      .rules()
      .then((r) => Object.fromEntries(r.rules.map((x) => [x.id, x.title])))
      .catch(() => ((pending = null), {}));
    let live = true;
    pending.then((t) => live && setTitles(t));
    return () => {
      live = false;
    };
  }, []);
  return id ? titles[id] : undefined;
}
