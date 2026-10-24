import { Fragment } from "react";

/** A page's title and, in plain words, what the page is for, with the plumb line hanging true beside it. */
export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="relative mb-4 border-b border-line pt-10 pb-8 sm:pt-16">
      <svg aria-hidden viewBox="0 0 60 200" preserveAspectRatio="xMidYMin meet" className="pointer-events-none absolute -top-6 right-2 hidden h-[calc(100%+1.5rem)] w-14 sm:block">
        <g className="plumb-swing" style={{ transformOrigin: "30px 0px" }}>
          <line x1="30" y1="0" x2="30" y2="132" stroke="#A39CFF" strokeWidth="1" strokeDasharray="3 3" />
          <path d="M30 132 L44 152 L30 180 L16 152 Z" fill="#4B3FD1" />
          <path d="M30 132 L44 152 L30 156 Z" fill="#fff" opacity=".15" />
        </g>
      </svg>
      <div className="relative sm:pr-20">
        <p className="font-label text-xs uppercase text-bone/50">Plumbline · Aurelle Skin</p>
        <h1 className="mt-3 font-display text-[clamp(2.5rem,6.5vw,5rem)] font-bold uppercase leading-[0.86] tracking-[-0.04em] text-bone">
          {title.split(" ").map((w, i) => (
            <Fragment key={i}>
              {i > 0 && " "}
              <span className="inline-block overflow-hidden pb-1 align-bottom">
                <span className="mask-up inline-block" style={{ animationDelay: `${i * 70}ms` }}>{w}</span>
              </span>
            </Fragment>
          ))}
        </h1>
        <p className="rise-in mt-4 max-w-2xl text-lg leading-snug text-bone/65" style={{ animationDelay: "200ms" }}>{subtitle}</p>
      </div>
    </header>
  );
}
