import { PageHeader } from "@/components/PageHeader";

import { HealthView } from "./HealthView";

export default function HealthPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader title="Guideline health" subtitle="How often reviewers agree with each rule. A rule they keep overruling is probably worded unclearly." />
      <HealthView />
    </main>
  );
}
