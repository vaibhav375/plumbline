"use client";

import { ReactLenis } from "lenis/react";
import { MotionConfig } from "motion/react";
import { useEffect, useState } from "react";

/** Smooth, weighted scrolling (Lenis) and Motion's animations, both off for people who ask for reduced motion. */
export function MotionRoot({ children }: { children: React.ReactNode }) {
  const [smooth, setSmooth] = useState(false);
  useEffect(() => setSmooth(!matchMedia("(prefers-reduced-motion: reduce)").matches), []);
  return (
    <MotionConfig reducedMotion="user">
      {smooth && <ReactLenis root options={{ lerp: 0.12, anchors: true }} />}
      {children}
    </MotionConfig>
  );
}
