import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">That page doesn&apos;t exist</h1>
      <p>
        The link may be old or mistyped. Go to <Link href="/check" className="underline underline-offset-4">Check content</Link>{" "}
        or the <Link href="/login" className="underline underline-offset-4">sign-in page</Link>.
      </p>
    </main>
  );
}
