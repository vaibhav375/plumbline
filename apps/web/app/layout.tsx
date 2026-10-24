import type { Metadata } from "next";
import { Archivo, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Archivo (Omnibus-Type), a grotesque with a width axis: one family, set wide and heavy for statements,
// condensed for labels, normal for reading. JetBrains Mono is the evidence (IDs, quotes, hashes).
const sans = Archivo({ variable: "--nf-sans", subsets: ["latin"], axes: ["wdth"] });
const mono = JetBrains_Mono({ variable: "--nf-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Plumbline",
  description: "Check marketing content against your brand's own rules and facts, before it's published.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${mono.variable} bg-carbon font-sans text-bone antialiased`}>
        {children}
      </body>
    </html>
  );
}
