import { AppHeader } from "@/components/AppHeader";

import { RulesTable } from "./RulesTable";

export default function RulesPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <AppHeader title="Rulebook" subtitle="Every rule the checker runs, where it comes from, and what the linter says about it." />
      <RulesTable />
    </main>
  );
}
