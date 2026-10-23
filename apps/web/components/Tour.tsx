"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

const KEY = "plumbline.tour.done";
const STEPS = [
  { title: "Start with a post", body: "Paste a draft, upload a file or image, or open the sample post to see a real check run straight away." },
  { title: "Every finding shows its evidence", body: "Each one names the rule or fact it comes from and the exact words. Blocking findings must be fixed, or sent to a reviewer with a note." },
  { title: "Fix, re-check, submit", body: "Accept approved-wording fixes, re-check, then submit. The check also lists what it couldn't check, so nothing slips through unseen." },
  { title: "Review and proof", body: "Reviewers decide in the queue and every decision lands in a tamper-evident audit log. 'How I know it works' shows how Plumbline was measured." },
];

// Storage can be blocked (private mode, cookies off); the tour then simply shows each visit.
const read = () => {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
};
const remember = () => {
  try {
    localStorage.setItem(KEY, "1");
  } catch {}
};

/** A 4-step first-visit tour. Inline and non-modal, so it never blocks the page. */
export function Tour() {
  const [step, setStep] = useState<number | null>(null);
  useEffect(() => {
    if (!read()) setStep(0);
  }, []);
  if (step === null) return null;
  const close = () => {
    remember();
    setStep(null);
  };
  const s = STEPS[step];
  return (
    <section role="dialog" aria-modal="false" aria-labelledby="tour-title"
      className="rounded-lg border-2 border-accent-brand bg-white p-4">
      <p id="tour-title" className="font-semibold">
        <span className="text-accent-brand">Step {step + 1} of {STEPS.length}:</span> {s.title}
      </p>
      <p className="mt-1 text-sm">{s.body}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {step > 0 && <Button size="sm" variant="outline" onClick={() => setStep(step - 1)}>Back</Button>}
        {step < STEPS.length - 1
          ? <Button size="sm" onClick={() => setStep(step + 1)}>Next</Button>
          : <Button size="sm" onClick={close}>Done</Button>}
        <Button size="sm" variant="ghost" onClick={close}>Skip tour</Button>
      </div>
    </section>
  );
}
