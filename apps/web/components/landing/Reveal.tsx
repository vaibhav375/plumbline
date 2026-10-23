"use client";

import { useEffect, useRef } from "react";

/** Rises into place the first time it scrolls into view. Without JS or with reduced motion it simply shows. */
export function Reveal({ children, className = "", delay = 0, as: Tag = "div" }: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  as?: "div" | "li" | "section" | "p";
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        el.classList.add("is-visible");
        io.disconnect();
      }
    }, { threshold: 0.12 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const El = Tag as React.ElementType;
  return (
    <El ref={ref} className={`reveal ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </El>
  );
}
