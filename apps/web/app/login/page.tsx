import { ArrowDown, ArrowRight, ArrowUpRight, BadgeCheck, Building2, ClipboardCheck, Megaphone, PenLine } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { Brandmark } from "@/components/Brandmark";
import { Intro } from "@/components/landing/Intro";
import { Parallax } from "@/components/landing/Parallax";
import { Reveal } from "@/components/landing/Reveal";
import latest from "@/public/eval/latest.json";

import { signInAs, type DemoRole } from "./actions";
import { RoleButton } from "./RoleButton";

const ROLES: { role: DemoRole; label: string; who: string; can: string; lands: string; icon: typeof PenLine }[] = [
  { role: "creator", label: "Creator", who: "Asha · in-house writer", can: "Check a draft privately, accept cited fixes and send it for review.", lands: "Check a post", icon: PenLine },
  { role: "agency", label: "Agency", who: "Sana · outside agency", can: "Check her own drafts. Confidential facts stay hidden from her.", lands: "Check a post", icon: Building2 },
  { role: "reviewer", label: "Reviewer", who: "Meera · content reviewer", can: "Work through the queue: agree or disagree with each finding, then approve.", lands: "Review queue", icon: BadgeCheck },
  { role: "compliance", label: "Compliance", who: "Arjun · compliance", can: "Decide claims and confidential findings, and give the compliance sign-off.", lands: "Review queue", icon: ClipboardCheck },
  { role: "brand_owner", label: "Brand owner", who: "Kabir · brand owner", can: "Own the rulebook and see which rules people find unclear.", lands: "Guideline health", icon: Megaphone },
];

const ERRORS: Record<string, string> = {
  signin: "Couldn't sign in to the demo account. Try again.",
  config: "Demo sign-in isn't configured on this deployment.",
};

// Real findings from the rulebook and fact ledger, for the ticker.
const TICKER = [
  ["“Clinically proven”", "needs a fact", "block"],
  ["“60% in 2 weeks”", "evidence says 32% in 8", "block"],
  ["“Eco-friendly”", "not substantiated", "block"],
  ["“Mumbai flagship”", "embargoed until December", "block"],
  ["Text at 1.96:1", "needs 3:1 contrast", "block"],
  ["“Click here”", "name the product", "minor"],
  ["“vit C serum”", "say Vitamin C Brightening Serum", "minor"],
  ["“Gifted by Aurelle”", "add #ad", "block"],
] as const;

const label = "font-label text-xs font-semibold uppercase tracking-[0.18em]";

/** A piece of content as it would go out, with the finding Plumbline raises on it. */
function Specimen({ kind, children, finding, tone = "block", className = "" }: {
  kind: string;
  children: React.ReactNode;
  finding: string;
  tone?: "block" | "minor";
  className?: string;
}) {
  return (
    <figure className={`group overflow-hidden rounded-xl bg-white text-ink shadow-[0_30px_60px_-30px_rgba(0,0,0,0.8)] ${className}`}>
      <div className="flex items-center justify-between border-b border-ink/10 px-3 py-2">
        <span className={`${label} text-[10px] text-ink/60`}>{kind}</span>
        <span className="size-1.5 rounded-full bg-ink/20" />
      </div>
      <div className="overflow-hidden">
        <div className="transition-transform duration-700 ease-out group-hover:scale-[1.04]">{children}</div>
      </div>
      <figcaption className={`flex items-center gap-2 px-3 py-2 text-xs font-semibold ${tone === "block" ? "bg-blocking text-white" : "bg-minor text-white"}`}>
        <span className="font-label uppercase tracking-wider">{tone === "block" ? "Blocks" : "Minor"}</span> {finding}
      </figcaption>
    </figure>
  );
}

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  const p = latest.results.plumbline.counts;
  const b = latest.results.baseline.counts;
  return (
    <div className="bg-white text-ink">
      <Intro />

      {/* ---------- Hero ---------- */}
      <header className="relative flex min-h-[100svh] flex-col overflow-hidden">
        <div aria-hidden className="guides contours pointer-events-none absolute inset-0" />
        <nav className="relative z-10 flex items-center justify-between px-5 py-5 sm:px-8">
          <Link href="/login" className="flex items-center gap-2">
            <Brandmark className="size-8 text-ink" />
            <span className="font-display text-xl font-extrabold uppercase tracking-tight">Plumbline</span>
          </Link>
          <div className="flex items-center gap-5 sm:gap-8">
            <Link href="/about" className={`${label} hidden text-ink/70 transition-colors hover:text-ink sm:block`}>How I know it works</Link>
            <Link href="/status" className={`${label} hidden text-ink/70 transition-colors hover:text-ink sm:block`}>Status</Link>
            <a href="#roles" className="group inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 font-display text-xs font-bold uppercase tracking-wide text-white transition-colors hover:bg-accent-brand">
              Try it <ArrowDown className="size-3.5 transition-transform group-hover:translate-y-0.5" aria-hidden />
            </a>
          </div>
        </nav>

        <div className="relative z-10 grid flex-1 items-center gap-10 px-5 pb-8 sm:px-8 lg:grid-cols-[1.2fr_1fr]">
          {/* The thesis, acted out: a claim is struck out and the approved wording takes its place. */}
          <div className="space-y-3">
            <p className={`${label} text-ink/60`}>Before it&apos;s published</p>
            <p className="font-display text-[clamp(2.4rem,5.6vw,5.4rem)] font-extrabold uppercase leading-[0.92] tracking-[-0.03em]">
              <span className="block">Every claim</span>
              <span className="block"><span className="strike-bg text-blocking">Clinically proven</span></span>
              <span className="swap-in block text-ok">Shown to visibly reduce*</span>
              <span className="block">Checked.</span>
            </p>
            <p className="font-mono text-xs text-ink/60">*FACT-014 · 32% fewer visible dark spots in 8 weeks · in-house study, 48 participants</p>
          </div>

          {/* The plumb bob as a window onto the content it checks: a scan line passes, a finding appears. */}
          <div className="relative mx-auto aspect-[5/6] w-full max-w-[250px] sm:max-w-[400px]">
            <svg viewBox="0 0 100 120" className="absolute inset-0 h-full w-full overflow-visible" aria-hidden>
              <defs>
                <clipPath id="bob"><path d="M50 4 L94 58 L50 116 L6 58 Z" /></clipPath>
              </defs>
              <line x1="50" y1="-12" x2="50" y2="4" stroke="#0B0B0C" strokeWidth="0.6" />
              <g clipPath="url(#bob)">
                {/* The banner's own cream and pink continue past its edges, so the window has no gaps. */}
                <rect width="100" height="120" fill="#FBF6EC" />
                <rect y="88" width="100" height="32" fill="#FF3EA5" />
                <image href="/images/aurelle-banner.png" x="14" y="6" width="104" height="104" preserveAspectRatio="xMidYMid slice" />
                <rect className="scan" x="0" y="0" width="100" height="1.2" fill="#4B3FD1" />
                <rect className="scan-glow" x="0" y="-14" width="100" height="14" fill="url(#glow)" />
              </g>
              <defs>
                <linearGradient id="glow" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0" stopColor="#4B3FD1" stopOpacity="0" />
                  <stop offset="1" stopColor="#4B3FD1" stopOpacity="0.28" />
                </linearGradient>
              </defs>
              <path d="M50 4 L94 58 L50 116 L6 58 Z" fill="none" stroke="#4B3FD1" strokeWidth="0.7" />
            </svg>
            <div className="finding-pop absolute top-[30%] -right-4 max-w-[200px] sm:max-w-[220px] rounded-lg bg-white p-3 text-xs shadow-[0_20px_40px_-20px_rgba(0,0,0,0.5)] ring-1 ring-ink/10 sm:-right-10">
              <p className="font-label text-[11px] font-semibold uppercase tracking-wider text-blocking">Blocks · A11Y-CONTRAST</p>
              <p className="mt-1 font-semibold text-ink">“GLOW IN 2 WEEKS” is 1.96:1. Large text needs 3:1.</p>
            </div>
            <span className={`${label} absolute -left-2 top-1/2 -translate-x-full -rotate-90 text-[10px] text-ink/50 max-lg:hidden`}>True vertical</span>
          </div>
        </div>

        <div className="relative z-10 flex items-end justify-between gap-6 px-5 pb-6 sm:px-8">
          <h1 className="max-w-3xl font-display text-xl font-bold uppercase leading-tight tracking-tight sm:text-2xl">
            Check marketing content against your brand&apos;s own rules and facts, before it&apos;s published.
          </h1>
          <a href="#how" className={`${label} hidden shrink-0 items-center gap-1 text-ink/70 hover:text-ink sm:inline-flex`}>
            Scroll down <ArrowDown className="size-3.5" aria-hidden />
          </a>
        </div>
      </header>

      {/* ---------- Ticker ---------- */}
      <div className="overflow-hidden border-y border-ink bg-ink py-3 text-white" aria-label="Examples of findings">
        <div className="marquee flex w-max gap-10 whitespace-nowrap">
          {[...TICKER, ...TICKER].map(([what, why, tone], i) => (
            <span key={i} className="flex items-center gap-3 font-display text-lg font-bold uppercase tracking-tight">
              <span className={`size-2 rotate-45 ${tone === "block" ? "bg-blocking" : "bg-minor"}`} aria-hidden />
              {what}
              <span className="font-label text-sm font-semibold tracking-[0.14em] text-white/55">{why}</span>
            </span>
          ))}
        </div>
      </div>

      {/* ---------- What goes out unchecked ---------- */}
      <section id="how" className="guides-dark relative overflow-hidden bg-ink px-5 pt-24 pb-16 text-white sm:px-8 sm:pt-32 sm:pb-24">
        <Reveal className="relative z-10 mx-auto max-w-5xl text-center">
          <p className={`${label} text-white/55`}>The problem</p>
          <h2 className="mt-3 font-display text-[clamp(2rem,5vw,4.2rem)] font-extrabold uppercase leading-[0.95] tracking-[-0.02em]">
            Content comes from everyone now. So do the mistakes.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-white/70">
            Writers, agencies, influencers and AI tools all post for the brand. The brand book is a PDF none of them has open.
          </p>
        </Reveal>

        <div className="relative mx-auto mt-20 grid max-w-6xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <Parallax speed={0.03}>
            <Specimen kind="Instagram post" finding="60% in 2 weeks: the evidence says 32% in 8">
              <div className="bg-gradient-to-br from-[#FDF1D6] to-[#F7D9A8] p-5">
                <div className="mx-auto h-32 w-14 rounded-t-full rounded-b-lg bg-gradient-to-b from-[#F2A541] to-[#D9731A] shadow-inner" />
              </div>
              <p className="p-3 text-sm">Meet the NEW Aurelle Vitamin-C serum!!! Clinically proven to fade dark spots by 60% in just 2 weeks.</p>
            </Specimen>
          </Parallax>
          <Parallax speed={0.07} className="lg:mt-16">
            <Specimen kind="Banner" finding="Headline text at 1.96:1 contrast; needs 3:1">
              <Image src="/images/aurelle-banner.png" alt="Aurelle banner with pale headline text" width={540} height={540} className="block aspect-[4/3] w-full object-cover" />
            </Specimen>
          </Parallax>
          <Parallax speed={0.02}>
            <Specimen kind="Email" finding="Mentions the embargoed Diwali sale (FACT-033)">
              <div className="space-y-2 p-4 text-sm">
                <p className="font-mono text-[11px] text-ink/50">Subject: Something big is coming 🎁</p>
                <p className="font-semibold">Our Diwali sale is here: 20% off everything.</p>
                <div className="h-2 w-3/4 rounded bg-ink/10" />
                <div className="h-2 w-1/2 rounded bg-ink/10" />
                <span className="inline-block rounded-md bg-ink px-3 py-1.5 text-xs font-bold text-white">Shop now</span>
              </div>
            </Specimen>
          </Parallax>
          <Parallax speed={0.05} className="lg:-mt-10">
            <Specimen kind="Influencer post" finding="Gifted, but no #ad label">
              <div className="flex items-center gap-3 p-4">
                <span className="size-10 rounded-full bg-gradient-to-br from-accent-brand to-[#E7A3C5]" />
                <div className="text-sm">
                  <p className="font-semibold">@glowwithsana</p>
                  <p className="text-ink/70">Gifted by Aurelle: I tried the SPF 50 Daily Sunscreen all week…</p>
                </div>
              </div>
            </Specimen>
          </Parallax>
          <Parallax speed={0.08} className="lg:mt-10">
            <Specimen kind="Product page" finding="“Dermatologist recommended”: no evidence on file">
              <div className="grid grid-cols-[72px_1fr] gap-3 p-4">
                <div className="h-20 rounded-lg bg-gradient-to-b from-[#E8F1FB] to-[#BFD6F2]" />
                <div className="space-y-1.5 text-sm">
                  <p className="font-semibold">Ceramide Barrier Cream</p>
                  <p className="text-ink/70">Dermatologist recommended and loved by thousands.</p>
                  <p className="font-mono text-xs">₹1,099</p>
                </div>
              </div>
            </Specimen>
          </Parallax>
          <Parallax speed={0.04}>
            <Specimen kind="Ad caption" finding="“Click here”: name the product instead" tone="minor">
              <p className="p-4 text-sm">Click here to see the new lip shades. Six shades, one easy swipe.</p>
            </Specimen>
          </Parallax>
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="guides relative px-5 py-24 sm:px-8 sm:py-32">
        <Reveal className="mx-auto max-w-6xl">
          <p className={`${label} text-ink/60`}>How it works</p>
          <h2 className="mt-3 max-w-4xl font-display text-[clamp(2rem,5vw,4.2rem)] font-extrabold uppercase leading-[0.95] tracking-[-0.02em]">
            Checked against <span className="text-accent-brand">your</span> rulebook and <span className="text-accent-brand">your</span> facts. With the evidence.
          </h2>
        </Reveal>
        <ol className="mx-auto mt-14 grid max-w-6xl gap-px overflow-hidden rounded-xl bg-ink/15 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["Paste or upload", "A draft, a DOCX, a PDF or an image. Text inside images is read too."],
            ["Rules run first", "Your banned phrases, required labels, product names, contrast and alt text, checked by code."],
            ["Claims meet the facts", "Every claim is matched to your fact ledger: supported, contradicted, expired or unsupported."],
            ["Evidence or silence", "A finding only shows if it names a real rule or fact and quotes your exact words."],
            ["Fixed without inventing", "Claims are fixed only with approved wording; your call to action and key phrases are kept."],
            ["Reviewed and recorded", "Reviewers decide, approvals are routed, and every step lands in a tamper-evident log."],
          ].map(([title, body], i) => (
            <Reveal as="li" key={title} delay={i * 70} className="group bg-white p-6 transition-colors duration-300 hover:bg-ink hover:text-white">
              <span className={`${label} text-ink/40 group-hover:text-white/50`}>Step {i + 1} of 6</span>
              <h3 className="mt-2 font-display text-xl font-bold uppercase tracking-tight">{title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-ink/70 group-hover:text-white/75">{body}</p>
            </Reveal>
          ))}
        </ol>
      </section>

      {/* ---------- Proof ---------- */}
      <section className="relative overflow-hidden bg-accent-brand px-5 py-24 text-white sm:px-8">
        <div aria-hidden className="guides-dark pointer-events-none absolute inset-0" />
        <Reveal className="relative mx-auto grid max-w-6xl items-end gap-10 lg:grid-cols-[1.1fr_1fr]">
          <div>
            <p className={`${label} text-white/70`}>Tested, not claimed</p>
            <h2 className="mt-3 font-display text-[clamp(2rem,5vw,4rem)] font-extrabold uppercase leading-[0.95] tracking-[-0.02em]">
              Finds {p.recall[0]} of {p.recall[1]} problems. A single AI prompt finds {b.recall[0]}.
            </h2>
            <p className="mt-4 max-w-xl text-white/80">
              On a {latest.dataset.n_items}-post test set with frozen labels, against one AI call given the whole brand book. Small set, wide
              intervals; the method and every number are public.
            </p>
            <Link href="/about" className="group mt-6 inline-flex items-center gap-2 border-b-2 border-white pb-1 font-display text-sm font-bold uppercase tracking-wide">
              See how it was tested <ArrowUpRight className="size-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </div>
          <div className="space-y-5">
            {[
              ["Plumbline", p.recall[0] / p.recall[1], `${p.recall[0]}/${p.recall[1]}`],
              ["One AI call", b.recall[0] / b.recall[1], `${b.recall[0]}/${b.recall[1]}`],
            ].map(([name, share, count]) => (
              <div key={name as string}>
                <div className="flex justify-between font-display text-sm font-bold uppercase">
                  <span>{name}</span><span className="tabular-nums">{count} found</span>
                </div>
                <div className="mt-2 h-4 overflow-hidden rounded-full bg-white/15">
                  <div className="h-full rounded-full bg-white" style={{ width: `${(share as number) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      {/* ---------- Try it ---------- */}
      <main id="roles" className="scroll-mt-4 bg-ink px-5 py-24 text-white sm:px-8">
        <Reveal className="mx-auto max-w-6xl">
          <p className={`${label} text-white/55`}>Try it as one of the team</p>
          <h2 className="mt-3 font-display text-[clamp(2rem,5vw,4.2rem)] font-extrabold uppercase leading-[0.95] tracking-[-0.02em]">
            Pick a role. No sign-up.
          </h2>
          <p className="mt-3 max-w-2xl text-white/70">Five demo accounts for Aurelle Skin, a fictional brand. Each one opens where its work is.</p>
        </Reveal>
        {error && (
          <p role="alert" className="mx-auto mt-6 max-w-6xl rounded-lg border border-blocking bg-white px-4 py-3 text-sm text-blocking">
            {ERRORS[error] ?? ERRORS.signin}
          </p>
        )}
        <ul className="mx-auto mt-12 grid max-w-6xl gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {ROLES.map(({ role, label: name, who, can, lands, icon: Icon }, i) => (
            <Reveal as="li" key={role} delay={i * 80}
              className="group flex flex-col justify-between gap-6 rounded-xl border border-white/15 bg-white/[0.03] p-5 transition-all duration-500 hover:-translate-y-1 hover:border-white/40 hover:bg-white/[0.07]">
              <div className="space-y-3">
                <span className="inline-flex size-10 items-center justify-center rounded-lg bg-white/10 text-white transition-colors duration-300 group-hover:bg-accent-brand">
                  <Icon className="size-5" aria-hidden />
                </span>
                <h3 className="font-display text-2xl font-extrabold uppercase tracking-tight">{name}</h3>
                <p className={`${label} text-[11px] text-white/50`}>{who}</p>
                <p className="text-[15px] leading-relaxed text-white/80">{can}</p>
              </div>
              <div className="space-y-3">
                <p className={`${label} flex items-center gap-1 text-[11px] text-white/50`}>
                  Opens <ArrowRight className="size-3" aria-hidden /> {lands}
                </p>
                <form action={signInAs.bind(null, role)}>
                  <RoleButton label={name} />
                </form>
              </div>
            </Reveal>
          ))}
        </ul>
      </main>

      {/* ---------- Close ---------- */}
      <section className="relative overflow-hidden bg-ink px-5 text-white sm:px-8">
        <div className="relative mx-auto flex max-w-6xl flex-col items-center border-t border-white/15 pt-24 pb-20 text-center">
          <Brandmark swing className="mb-8 size-16 text-white/80" />
          <p className="font-display text-[clamp(2.2rem,6vw,5rem)] font-extrabold uppercase leading-[0.9] tracking-[-0.03em]">
            Silence is never clearance.
          </p>
          <a href="#roles" className="mt-6 font-display text-[clamp(1.4rem,3.4vw,2.6rem)] font-extrabold uppercase underline decoration-[3px] underline-offset-[10px] transition-colors hover:text-[#A9A2F7]">
            Check your first post
          </a>
        </div>
      </section>
      <footer className="bg-ink px-5 pb-10 text-white sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 border-t border-white/15 pt-6">
          <span className={`${label} text-white/50`}>Evidence or silence.</span>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <Link href="/status" className={`${label} text-white/70 hover:text-white`}>Status</Link>
            <Link href="/about" className={`${label} text-white/70 hover:text-white`}>How I know it works</Link>
            <span className={`${label} text-white/50`}>Aurelle Skin is a fictional brand; no real data is used.</span>
          </div>
          <span className={`${label} text-white/50`}>Demo runs on free model tiers with fictional data only.</span>
        </div>
      </footer>
    </div>
  );
}
