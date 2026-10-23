import { AppHeader } from "@/components/AppHeader";

import { CheckForm } from "./CheckForm";

export default function CheckPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <AppHeader
        title="Check content"
        subtitle="Paste a draft or upload a file. Plumbline checks it against Aurelle's rules and facts, and shows what it couldn't check."
      />
      <CheckForm />
    </main>
  );
}
