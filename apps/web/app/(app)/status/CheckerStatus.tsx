"use client";

import { useEffect, useState } from "react";

type Health = { status: string; version: string; providers: Record<string, boolean>; db: boolean };
const CHECKER = process.env.NEXT_PUBLIC_CHECKER_URL!;

const Row = ({ name, ok, detail }: { name: string; ok: boolean; detail?: string }) => (
  <div className="flex items-center justify-between gap-3 border-t px-4 py-3 first:border-t-0">
    <dt>{name}</dt>
    <dd className={`font-medium ${ok ? "text-ok" : "text-blocking"}`}>
      {ok ? "✓ Available" : "✗ Unavailable"}
      {detail && <span className="ml-2 text-xs font-normal text-muted-foreground">{detail}</span>}
    </dd>
  </div>
);

export function CheckerStatus() {
  const [state, setState] = useState<"checking" | "up" | "down">("checking");
  const [health, setHealth] = useState<Health | null>(null);
  const [ms, setMs] = useState<number | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 45_000); // long enough for a cold start
    const t0 = performance.now();
    fetch(`${CHECKER}/health`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((h: Health) => (setHealth(h), setMs(Math.round(performance.now() - t0)), setState("up")))
      .catch(() => setState("down"))
      .finally(() => clearTimeout(timer));
    return () => ctrl.abort();
  }, []);

  return (
    <section aria-labelledby="checker" className="rounded-xl bg-panel shadow-sm ring-1 ring-line">
      <h2 id="checker" className="flex items-center justify-between gap-3 px-4 pt-4 font-semibold">
        Checker
        <span data-testid="checker-status" className={state === "up" ? "text-ok" : state === "down" ? "text-blocking" : "text-major"}>
          {state === "up" ? "Up" : state === "down" ? "Down" : "Waking or checking…"}
        </span>
      </h2>
      <p className="px-4 pb-3 text-xs text-muted-foreground">
        {state === "up" && health ? `Version ${health.version} · answered in ${ms} ms` : state === "down" ? "No answer within 45 s. Try again in a minute." : "Asking the checker…"}
      </p>
      {health && (
        <dl className="text-sm">
          <Row name="Groq (first choice)" ok={health.providers.groq} />
          <Row name="Gemini (fallback)" ok={health.providers.gemini} />
          <Row name="Database" ok={health.db} />
        </dl>
      )}
    </section>
  );
}
