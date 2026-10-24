import type { Metadata } from "next";
import { Archivo, JetBrains_Mono, Jost } from "next/font/google";
import "lenis/dist/lenis.css";
import "./globals.css";

import { MotionRoot } from "@/components/Motion";

// Set the way Podium sets Futura: Jost, an open Futura revival, bold and uppercase with tight tracking for
// titles and plain for reading; Archivo at its narrowest width for small labels (Podium uses Univers
// Condensed there). JetBrains Mono is the evidence (IDs, quotes, hashes).
const sans = Jost({ variable: "--nf-sans", subsets: ["latin"] });
const label = Archivo({ variable: "--nf-label", subsets: ["latin"], axes: ["wdth"] });
const mono = JetBrains_Mono({ variable: "--nf-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Plumbline",
  description: "Check marketing content against your brand's own rules and facts, before it's published.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${label.variable} ${mono.variable} bg-carbon font-sans text-bone antialiased`}>
        <MotionRoot>{children}</MotionRoot>
      </body>
    </html>
  );
}
