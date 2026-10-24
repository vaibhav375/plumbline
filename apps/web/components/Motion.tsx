"use client";

import { ReactLenis } from "lenis/react";
import { MotionConfig } from "motion/react";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/** Smooth, weighted scrolling (Lenis) and Motion's animations, both off for people who ask for reduced motion. */
export function MotionRoot({ children }: { children: React.ReactNode }) {
  const [smooth, setSmooth] = useState(false);
  useEffect(() => setSmooth(!matchMedia("(prefers-reduced-motion: reduce)").matches), []);

  // A new page opens at the top. Lenis otherwise carried the old position across the sign-in
  // redirect (signing in from far down the landing page opened /check scrolled 180 px down).
  // Back and Forward keep the browser's own restored position.
  const path = usePathname();
  const historyMove = useRef(false);
  useEffect(() => {
    const onPop = () => (historyMove.current = true);
    addEventListener("popstate", onPop);
    return () => removeEventListener("popstate", onPop);
  }, []);
  useEffect(() => {
    if (historyMove.current) historyMove.current = false;
    else if (!location.hash) window.scrollTo(0, 0);
  }, [path]);

  return (
    <MotionConfig reducedMotion="user">
      {smooth && <ReactLenis root options={{ lerp: 0.12, anchors: true }} />}
      {children}
    </MotionConfig>
  );
}
