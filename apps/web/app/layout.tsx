import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Plumbline",
  description: "Evidence-or-silence content checks for brand and compliance teams.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
        <footer className="mx-auto flex max-w-6xl flex-wrap gap-x-4 gap-y-1 border-t px-4 py-4 text-sm text-muted-foreground sm:px-6">
          <Link href="/status" className="underline-offset-4 hover:underline">Status</Link>
          <Link href="/about" className="underline-offset-4 hover:underline">How I know it works</Link>
          <span>Aurelle Skin is a fictional brand; no real data is used.</span>
        </footer>
      </body>
    </html>
  );
}
