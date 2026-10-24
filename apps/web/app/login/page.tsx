import { ArrowDown, ArrowRight, ArrowUpRight, BadgeCheck, Building2, ClipboardCheck, Heart, Megaphone, MessageCircle, PenLine, Send } from "lucide-react";
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

const label = "font-label text-xs font-semibold uppercase";

/** A piece of content as it would go out, with the finding Plumbline raises on it pinned underneath. */
function Specimen({ kind, children, finding, tone = "block", className = "" }: {
  kind: string;
  children: React.ReactNode;
  finding: string;
  tone?: "block" | "minor";
  className?: string;
}) {
  return (
    <figure className={`group ${className}`}>
      <div className="paper overflow-hidden rounded-md text-ink">
        <div className="flex items-center justify-between border-b border-ink/10 px-3 py-2">
          <span className="font-label text-[11px] text-ink/60 uppercase">{kind}</span>
          <span className="flex gap-1" aria-hidden><span className="size-1.5 rounded-full bg-ink/20" /><span className="size-1.5 rounded-full bg-ink/20" /></span>
        </div>
        {children}
      </div>
      <figcaption className="mt-2 flex items-start gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm text-bone">
        <span aria-hidden className={`mt-1.5 size-2 shrink-0 rotate-45 ${tone === "block" ? "bg-blocking" : "bg-minor"}`} />
        <span>
          <span className={`font-label text-xs uppercase ${tone === "block" ? "text-blocking" : "text-minor"}`}>{tone === "block" ? "Blocks" : "Minor"} </span>
          {finding}
        </span>
      </figcaption>
    </figure>
  );
}

/** The words Plumbline flags, underlined in the severity colour the way the checker marks them. */
const Flag = ({ children, tone = "block" }: { children: React.ReactNode; tone?: "block" | "minor" }) => (
  <span className="rounded-sm px-0.5" style={{ boxShadow: `inset 0 -3px 0 ${tone === "block" ? "#FF6A5C" : "#74A7F0"}`, background: tone === "block" ? "#FF6A5C1f" : "#74A7F01f" }}>{children}</span>
);

/** Photos sit in a frame that scales them slowly on hover, as Podium does with its media. */
const Photo = ({ src, alt, className = "aspect-square" }: { src: string; alt: string; className?: string }) => (
  <div className={`relative overflow-hidden ${className}`}>
    <Image src={src} alt={alt} fill sizes="(min-width: 1024px) 380px, (min-width: 640px) 50vw, 100vw"
      className="object-cover transition-transform duration-700 ease-[cubic-bezier(0,0,.2,1)] group-hover:scale-[1.05]" />
  </div>
);

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  const p = latest.results.plumbline.counts;
  const b = latest.results.baseline.counts;
  return (
    <div className="bg-carbon text-bone">
      <Intro />

      {/* ---------- Hero ---------- */}
      <header className="relative flex min-h-[100svh] flex-col overflow-hidden">
        <div aria-hidden className="guides contours pointer-events-none absolute inset-0" />
        <nav className="relative z-10 flex items-center justify-between px-5 py-5 sm:px-8">
          <Link href="/login" className="flex items-center gap-2">
            <Brandmark className="size-8 text-bone" />
            <span className="font-display text-xl font-bold uppercase tracking-tight">Plumbline</span>
          </Link>
          <div className="flex items-center gap-5 sm:gap-8">
            <Link href="/about" className={`hidden font-display text-sm font-bold tracking-[-0.02em] text-bone/70 uppercase transition-colors hover:text-bone sm:block`}>How I know it works</Link>
            <Link href="/status" className={`hidden font-display text-sm font-bold tracking-[-0.02em] text-bone/70 uppercase transition-colors hover:text-bone sm:block`}>Status</Link>
            <a href="#roles" className="group inline-flex items-center gap-1.5 rounded-full bg-bone px-4 py-2 font-display text-xs font-bold uppercase tracking-wide text-carbon transition-colors hover:bg-accent-brand hover:text-white">
              Try it <ArrowDown className="size-3.5 transition-transform group-hover:translate-y-0.5" aria-hidden />
            </a>
          </div>
        </nav>

        <div className="relative z-10 grid flex-1 items-center gap-10 px-5 pb-8 sm:px-8 lg:grid-cols-[1.2fr_1fr]">
          {/* The thesis, acted out: a claim is struck out and the approved wording takes its place. */}
          <div className="space-y-3">
            <p className={`${label} text-bone/60`}>Before it&apos;s published</p>
            <p className="font-display text-[clamp(2.4rem,5.6vw,5.4rem)] font-bold uppercase leading-[0.92] tracking-[-0.03em]">
              <span className="block">Every claim</span>
              <span className="block"><span className="strike-bg text-blocking">Clinically proven</span></span>
              <span className="swap-in block text-ok">Shown to visibly reduce*</span>
              <span className="block">Checked.</span>
            </p>
            <p className="font-mono text-xs text-bone/60">*FACT-014 · 32% fewer visible dark spots in 8 weeks · in-house study, 48 participants</p>
          </div>

          {/* A real-looking ad on the table: the serum's drip runs straight down like a plumb line, and Plumbline
              boxes the headline it can't pass (white on this orange measures 1.96:1). */}
          <div className="relative mx-auto w-full max-w-[300px] sm:max-w-[360px]">
            <span aria-hidden className="absolute -top-[40vh] left-[51.5%] h-[40vh] w-px bg-gradient-to-b from-transparent to-[#F7E7D2]/80" />
            <figure className="relative aspect-[1000/1481] overflow-hidden rounded-sm shadow-[0_40px_80px_-30px_rgba(0,0,0,0.9)]">
              <Image src="/images/serum-amber-orange.jpg" alt="A sample Aurelle ad: a Vitamin C serum bottle on orange, headline “Glow in 2 weeks” in white"
                fill priority sizes="(min-width: 640px) 360px, 300px" className="object-cover" />
              <p aria-hidden className="absolute top-[6%] left-[7%] font-display text-[clamp(1.9rem,3.4vw,2.6rem)] leading-[0.88] font-bold tracking-[-0.03em] text-white uppercase">
                Glow in<br />2 weeks
              </p>
              <div aria-hidden className="absolute top-[67%] left-[33.5%] flex h-[21%] w-[30.5%] flex-col items-center justify-center gap-0.5 text-center text-[#2A1A0E]">
                <span className="font-display text-[clamp(0.7rem,1.2vw,0.95rem)] leading-none font-bold tracking-[-0.02em] uppercase">Aurelle</span>
                <span className="font-label text-[clamp(0.45rem,0.75vw,0.6rem)] leading-tight uppercase">Vitamin C<br />Brightening Serum</span>
                <span className="font-label text-[clamp(0.4rem,0.65vw,0.5rem)] uppercase opacity-70">30 ml</span>
              </div>
              <div aria-hidden className="scan-y absolute inset-x-0 h-14 bg-gradient-to-b from-transparent via-[#A39CFF]/35 to-transparent" />
              <div aria-hidden className="box-in absolute top-[4.5%] left-[5%] h-[17%] w-[50%] border-2 border-dashed border-blocking" />
            </figure>
            <div className="finding-pop paper absolute top-[7%] -right-3 max-w-[210px] rounded-lg p-3 text-xs sm:-right-24">
              <p className="font-label text-[11px] font-semibold text-[#B3261E] uppercase">Blocks · A11Y-CONTRAST</p>
              <p className="mt-1 font-semibold text-ink">“GLOW IN 2 WEEKS” is 1.96:1. Large text needs 3:1.</p>
            </div>
            <span className={`${label} absolute top-1/2 -left-3 -translate-x-full -rotate-90 text-[10px] text-bone/50 max-lg:hidden`}>True vertical</span>
          </div>
        </div>

        <div className="relative z-10 flex items-end justify-between gap-6 px-5 pb-6 sm:px-8">
          <h1 className="max-w-3xl font-display text-xl font-bold uppercase leading-tight tracking-tight sm:text-2xl">
            Check marketing content against your brand&apos;s own rules and facts, before it&apos;s published.
          </h1>
          <a href="#how" className={`${label} hidden shrink-0 items-center gap-1 text-bone/70 hover:text-bone sm:inline-flex`}>
            Scroll down <ArrowDown className="size-3.5" aria-hidden />
          </a>
        </div>
      </header>

      {/* ---------- Ticker ---------- */}
      <div className="overflow-hidden border-y border-line bg-panel py-3 text-bone" aria-label="Examples of findings">
        <div className="marquee flex w-max gap-10 whitespace-nowrap">
          {[...TICKER, ...TICKER].map(([what, why, tone], i) => (
            <span key={i} className="flex items-center gap-3 font-display text-lg font-bold uppercase tracking-tight">
              <span className={`size-2 rotate-45 ${tone === "block" ? "bg-blocking" : "bg-minor"}`} aria-hidden />
              {what}
              <span className="font-label text-sm font-semibold text-white/55">{why}</span>
            </span>
          ))}
        </div>
      </div>

      {/* ---------- What goes out unchecked ---------- */}
      <section id="how" className="guides-dark relative overflow-hidden bg-carbon px-5 pt-24 pb-16 text-white sm:px-8 sm:pt-32 sm:pb-24">
        <Reveal className="relative z-10 mx-auto max-w-5xl text-center">
          <p className={`${label} text-white/55`}>The problem</p>
          <h2 className="mt-3 font-display text-[clamp(2rem,5vw,4.2rem)] font-bold uppercase leading-[0.95] tracking-[-0.02em]">
            Content comes from everyone now. So do the mistakes.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-white/70">
            Writers, agencies, influencers and AI tools all post for the brand. The brand book is a PDF none of them has open.
          </p>
        </Reveal>

        <div className="relative mx-auto mt-20 grid max-w-6xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <Parallax speed={0.03}>
            <Specimen kind="Instagram post" finding="60% in 2 weeks: the evidence says 32% in 8 (FACT-014)">
              <div className="flex items-center gap-2 px-3 py-2">
                <span className="flex size-7 items-center justify-center rounded-full bg-[#E8892B] font-display text-[10px] font-bold text-white">A</span>
                <span className="text-sm font-semibold">aurelle.skin</span>
                <span className="ml-auto text-xs text-ink/50">Sponsored</span>
              </div>
              <Photo src="/images/serum-shadow.jpg" alt="An amber dropper bottle in afternoon light" className="aspect-[4/5]" />
              <p className="flex gap-3 px-3 pt-2 text-ink/70" aria-hidden><Heart className="size-5" /><MessageCircle className="size-5" /><Send className="size-5" /></p>
              <p className="px-3 pt-1 pb-3 text-sm leading-relaxed">
                <b>aurelle.skin</b> Meet the NEW Vitamin C serum! Clinically proven to fade dark spots <Flag>by 60% in just 2 weeks</Flag>.
              </p>
            </Specimen>
          </Parallax>
          <Parallax speed={0.07} className="lg:mt-24">
            <Specimen kind="Web banner" finding="“Glow in 2 weeks”: the evidence covers 8 weeks, not 2 (FACT-014)">
              <div className="relative">
                <Photo src="/images/textures-flatlay.jpg" alt="Serum and gel textures on glass discs" className="aspect-[4/3]" />
                <p className="absolute top-4 left-4 font-display text-3xl leading-[0.95] font-bold tracking-[-0.03em] text-ink uppercase">
                  Glow in<br /><Flag>2 weeks</Flag>
                </p>
                <span className="absolute right-4 bottom-3 font-display text-sm font-bold tracking-[-0.02em] text-ink uppercase">Aurelle</span>
              </div>
            </Specimen>
          </Parallax>
          <Parallax speed={0.02}>
            <Specimen kind="Email" finding="Announces the Diwali sale while it's still embargoed (FACT-033)">
              <div className="space-y-0.5 border-b border-ink/10 px-4 py-2.5 text-xs">
                <p><span className="text-ink/50">From</span> Aurelle Skin</p>
                <p><span className="text-ink/50">Subject</span> <b>Something big is coming</b></p>
              </div>
              <Photo src="/images/textures-leaves.jpg" alt="Skincare textures with green leaves" className="aspect-[16/9]" />
              <div className="space-y-3 p-4">
                <p className="font-display text-xl leading-tight font-bold tracking-[-0.02em] uppercase"><Flag>Our Diwali sale is here: 20% off</Flag> everything.</p>
                <span className="inline-block rounded-full bg-ink px-4 py-1.5 font-display text-xs font-bold text-white uppercase">Shop now</span>
              </div>
            </Specimen>
          </Parallax>
          <Parallax speed={0.05} className="lg:-mt-16">
            <Specimen kind="Influencer post" finding="Gifted product, but no #ad label">
              <div className="flex items-center gap-2 px-3 py-2">
                <span className="size-7 rounded-full bg-gradient-to-br from-[#E7A3C5] to-[#8A80F2]" />
                <span className="text-sm font-semibold">glowwithsana</span>
              </div>
              <Photo src="/images/applying-serum.jpg" alt="Someone pressing serum into their cheek" className="aspect-[3/2]" />
              <p className="px-3 py-3 text-sm leading-relaxed">
                <b>glowwithsana</b> <Flag>Gifted by Aurelle</Flag>: two weeks with the Vitamin C serum and my skin has never been calmer ✨
              </p>
            </Specimen>
          </Parallax>
          <Parallax speed={0.08} className="lg:mt-8">
            <Specimen kind="Product page" finding="“Dermatologist recommended”: no evidence on file">
              <Photo src="/images/cream-jar.jpg" alt="A jar of cream on marble with carnations" className="aspect-[3/2]" />
              <div className="space-y-1.5 p-4">
                <p className="font-display text-lg leading-tight font-bold tracking-[-0.02em] uppercase">Ceramide Barrier Cream</p>
                <p className="text-sm text-ink/75"><Flag>Dermatologist recommended</Flag> and loved by thousands.</p>
                <div className="flex items-center justify-between pt-1">
                  <span className="font-mono text-sm">₹1,099</span>
                  <span className="rounded-full bg-ink px-4 py-1.5 font-display text-xs font-bold text-white uppercase">Add to bag</span>
                </div>
              </div>
            </Specimen>
          </Parallax>
          <Parallax speed={0.04} className="lg:-mt-8">
            <Specimen kind="Ad caption" finding="“Click here” says nothing; name the product" tone="minor">
              <Photo src="/images/lip-gloss-pink.jpg" alt="A pink lip gloss on a pink background" className="aspect-[4/3]" />
              <p className="p-4 text-sm leading-relaxed"><Flag tone="minor">Click here</Flag> to see the new lip shades. Six shades, one easy swipe.</p>
            </Specimen>
          </Parallax>
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="guides relative px-5 py-24 sm:px-8 sm:py-32">
        <Reveal className="mx-auto max-w-6xl">
          <p className={`${label} text-bone/60`}>How it works</p>
          <h2 className="mt-3 max-w-4xl font-display text-[clamp(2rem,5vw,4.2rem)] font-bold uppercase leading-[0.95] tracking-[-0.02em]">
            Checked against <span className="text-iris">your</span> rulebook and <span className="text-iris">your</span> facts. With the evidence.
          </h2>
        </Reveal>
        <ol className="mx-auto mt-14 grid max-w-6xl gap-px overflow-hidden rounded-xl bg-line sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["Paste or upload", "A draft, a DOCX, a PDF or an image. Text inside images is read too."],
            ["Rules run first", "Your banned phrases, required labels, product names, contrast and alt text, checked by code."],
            ["Claims meet the facts", "Every claim is matched to your fact ledger: supported, contradicted, expired or unsupported."],
            ["Evidence or silence", "A finding only shows if it names a real rule or fact and quotes your exact words."],
            ["Fixed without inventing", "Claims are fixed only with approved wording; your call to action and key phrases are kept."],
            ["Reviewed and recorded", "Reviewers decide, approvals are routed, and every step lands in a tamper-evident log."],
          ].map(([title, body], i) => (
            <Reveal as="li" key={title} delay={i * 70} className="group bg-panel p-6 transition-colors duration-300 hover:bg-bone hover:text-carbon">
              <span className={`${label} text-bone/45 group-hover:text-carbon/60`}>Step {i + 1} of 6</span>
              <h3 className="mt-2 font-display text-xl font-bold uppercase tracking-tight">{title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-bone/70 group-hover:text-carbon/75">{body}</p>
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
            <h2 className="mt-3 font-display text-[clamp(2rem,5vw,4rem)] font-bold uppercase leading-[0.95] tracking-[-0.02em]">
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
      <main id="roles" className="scroll-mt-4 border-t border-line bg-panel px-5 py-24 text-white sm:px-8">
        <Reveal className="mx-auto max-w-6xl">
          <p className={`${label} text-white/55`}>Try it as one of the team</p>
          <h2 className="mt-3 font-display text-[clamp(2rem,5vw,4.2rem)] font-bold uppercase leading-[0.95] tracking-[-0.02em]">
            Pick a role. No sign-up.
          </h2>
          <p className="mt-3 max-w-2xl text-white/70">Five demo accounts for Aurelle Skin, a fictional brand. Each one opens where its work is.</p>
        </Reveal>
        {error && (
          <p role="alert" className="mx-auto mt-6 max-w-6xl rounded-lg border border-blocking bg-blocking/10 px-4 py-3 text-sm text-blocking">
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
                <h3 className="font-display text-2xl font-bold uppercase tracking-tight">{name}</h3>
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
          <p className="font-display text-[clamp(2.2rem,6vw,5rem)] font-bold uppercase leading-[0.9] tracking-[-0.03em]">
            Silence is never clearance.
          </p>
          <a href="#roles" className="mt-6 font-display text-[clamp(1.4rem,3.4vw,2.6rem)] font-bold uppercase underline decoration-[3px] underline-offset-[10px] transition-colors hover:text-[#A9A2F7]">
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
