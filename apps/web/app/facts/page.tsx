import { AppHeader } from "@/components/AppHeader";

import { FactLedger } from "./FactLedger";

export default function FactsPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <AppHeader title="Fact ledger" subtitle="The claims the brand can back up, and the approved ways to say them." />
      <FactLedger />
    </main>
  );
}
