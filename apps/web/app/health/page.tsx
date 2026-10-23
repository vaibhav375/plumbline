import { AppHeader } from "@/components/AppHeader";

import { HealthView } from "./HealthView";

export default function HealthPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <AppHeader title="Guideline health" subtitle="Do reviewers agree with each rule's flags? Rules they keep overruling may be unclear." />
      <HealthView />
    </main>
  );
}
