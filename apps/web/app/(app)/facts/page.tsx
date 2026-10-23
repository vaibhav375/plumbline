import { PageHeader } from "@/components/PageHeader";

import { FactLedger } from "./FactLedger";

export default function FactsPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader title="Fact ledger" subtitle="The claims Aurelle can back up with evidence, and the approved way to say each one." />
      <FactLedger />
    </main>
  );
}
