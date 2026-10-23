/** The plumb line and its bob: a weight on a string that shows true vertical. */
export function Brandmark({ className = "", swing = false }: { className?: string; swing?: boolean }) {
  return (
    <svg viewBox="0 0 34 34" aria-hidden className={className}>
      <line x1="6" y1="2" x2="28" y2="2" stroke="currentColor" strokeWidth="1.6" />
      <g className={swing ? "plumb-swing" : undefined} style={{ transformOrigin: "17px 2px" }}>
        <line x1="17" y1="2" x2="17" y2="19" stroke="#8B82F0" strokeWidth="1.6" />
        <path d="M17 19 L25 25 L17 33 L9 25 Z" fill="#4B3FD1" />
      </g>
    </svg>
  );
}
