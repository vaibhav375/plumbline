import { PageHeader } from "@/components/PageHeader";

import { RulesTable } from "./RulesTable";

export default function RulesPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader title="Rulebook" subtitle="Everything the checker looks for, where each rule comes from, and which rules are too vague to check." />
      <RulesTable />
    </main>
  );
}
