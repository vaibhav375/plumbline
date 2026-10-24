"use client";

import { useEffect, useState } from "react";

import { ruleTitles } from "@/lib/api";

// One request per visit: every finding card reads the same map. A failure leaves cards with just the code.
let pending: Promise<Record<string, string>> | null = null;

/** The plain-English title of a rule (e.g. "At most one exclamation mark" for TN-02), once loaded. */
export function useRuleTitle(id: string | null | undefined): string | undefined {
  const [titles, setTitles] = useState<Record<string, string>>({});
  useEffect(() => {
    pending ??= ruleTitles().then((t) => {
      if (!Object.keys(t).length) pending = null; // try again on the next page
      return t;
    });
    let live = true;
    pending.then((t) => live && setTitles(t));
    return () => {
      live = false;
    };
  }, []);
  return id ? titles[id] : undefined;
}
