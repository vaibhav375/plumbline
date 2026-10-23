import { PageHeader } from "@/components/PageHeader";
import { Tour } from "@/components/Tour";

import { CheckForm } from "./CheckForm";

export default function CheckPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader
        title="Check a post"
        subtitle="Paste a draft or upload a file. You'll see what breaks Aurelle's rules, which claims the evidence doesn't back, and the approved way to say it."
      />
      <Tour />
      <CheckForm />
    </main>
  );
}
