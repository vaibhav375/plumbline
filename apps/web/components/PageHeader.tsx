import { Fragment } from "react";

/** A page's title and, in plain words, what the page is for, over the drafting texture, with the plumb line hanging true. */
export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="relative -mx-4 -mt-4 mb-2 overflow-hidden border-b border-line bg-panel px-4 pt-10 pb-9 sm:-mx-6 sm:-mt-6 sm:px-6 sm:pt-14">
      <div aria-hidden className="guides contours pointer-events-none absolute inset-0 opacity-70" />
      <svg aria-hidden viewBox="0 0 60 200" preserveAspectRatio="xMidYMin meet" className="pointer-events-none absolute top-0 right-6 hidden h-full w-16 sm:block lg:right-12">
        <g className="plumb-swing" style={{ transformOrigin: "30px 0px" }}>
          <line x1="30" y1="0" x2="30" y2="128" stroke="#A39CFF" strokeWidth="1" strokeDasharray="3 3" />
          <path d="M30 128 L44 148 L30 176 L16 148 Z" fill="#4B3FD1" />
          <path d="M30 128 L44 148 L30 152 Z" fill="#fff" opacity=".15" />
        </g>
      </svg>
      <div className="relative space-y-3 sm:pr-24">
        <p className="font-label text-xs font-semibold uppercase tracking-[0.18em] text-bone/55">Plumbline · Aurelle Skin</p>
        <h1 className="font-display text-4xl font-extrabold uppercase leading-[0.92] tracking-[-0.025em] text-bone sm:text-6xl lg:text-7xl">
          {title.split(" ").map((w, i) => (
            <Fragment key={i}>
              {i > 0 && " "}
              <span className="inline-block overflow-hidden pb-1 align-bottom">
                <span className="mask-up inline-block" style={{ animationDelay: `${i * 70}ms` }}>{w}</span>
              </span>
            </Fragment>
          ))}
        </h1>
        <p className="rise-in max-w-3xl text-base text-bone/70" style={{ animationDelay: "200ms" }}>{subtitle}</p>
      </div>
      <div aria-hidden className="ruler absolute inset-x-0 bottom-0 h-2.5" />
    </header>
  );
}
