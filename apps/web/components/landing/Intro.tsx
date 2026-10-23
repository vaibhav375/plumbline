"use client";

import { useEffect, useState } from "react";

/** A 1.5 s intro: the plumb bob drops on its line, a counter runs to 100%, the curtain lifts.
 * It never blocks clicks (pointer-events: none), and is skipped after the first visit in a session. */
export function Intro() {
  const [show, setShow] = useState(false);
  const [n, setN] = useState(0);
  useEffect(() => {
    let seen = false;
    try { seen = sessionStorage.getItem("plumbline.intro") === "1"; sessionStorage.setItem("plumbline.intro", "1"); } catch {}
    if (seen || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    setShow(true);
    const t0 = performance.now();
    let raf = requestAnimationFrame(function tick(t) {
      const p = Math.min(1, (t - t0) / 1000);
      setN(Math.round(p * 100));
      if (p < 1) raf = requestAnimationFrame(tick);
    });
    const done = setTimeout(() => setShow(false), 1600);
    return () => { cancelAnimationFrame(raf); clearTimeout(done); };
  }, []);
  if (!show) return null;
  return (
    <div aria-hidden className="curtain pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-white">
      <div className="flex flex-col items-center">
        <span className="h-24 w-0.5 origin-top bg-ink" />
        <svg viewBox="0 0 20 24" className="drop -mt-px h-8 w-7"><path d="M10 0 L20 12 L10 24 L0 12 Z" fill="#4B3FD1" /></svg>
      </div>
      <span className="absolute top-6 right-6 font-display text-sm font-bold tabular-nums">{n}%</span>
      <span className="absolute bottom-6 left-6 font-label text-xs font-semibold uppercase tracking-[0.2em] text-ink/60">Finding true vertical</span>
    </div>
  );
}
