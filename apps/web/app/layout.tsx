import type { Metadata } from "next";
import { Bricolage_Grotesque, JetBrains_Mono, Public_Sans } from "next/font/google";
import "./globals.css";

// Display: characterful, for page titles only. Body: plain and civic. Mono: the evidence (IDs, quotes, hashes).
const display = Bricolage_Grotesque({ variable: "--nf-display", subsets: ["latin"], weight: ["500", "700"] });
const body = Public_Sans({ variable: "--nf-body", subsets: ["latin"] });
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
