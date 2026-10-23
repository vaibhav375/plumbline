import type { Metadata } from "next";
import { Barlow_Condensed, JetBrains_Mono, Jost } from "next/font/google";
import "./globals.css";

// Jost: a geometric sans in the Futura tradition, set bold and uppercase for statements, plain for text.
// Barlow Condensed: small uppercase labels, like a surveyor's notes. Mono: the evidence (IDs, quotes, hashes).
const display = Jost({ variable: "--nf-display", subsets: ["latin"], weight: ["400", "500", "600", "700", "800"] });
const body = Barlow_Condensed({ variable: "--nf-body", subsets: ["latin"], weight: ["500", "600", "700"] });
const mono = JetBrains_Mono({ variable: "--nf-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Plumbline",
  description: "Check marketing content against your brand's own rules and facts, before it's published.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} ${mono.variable} bg-chalk font-sans text-ink antialiased`}>
        {children}
      </body>
    </html>
  );
}
