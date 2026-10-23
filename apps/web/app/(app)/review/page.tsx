import { PageHeader } from "@/components/PageHeader";

import { Queue } from "./Queue";

export default function ReviewPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader title="Review queue" subtitle="Posts sent for review, riskiest first. Drafts people check privately never appear here." />
      <Queue />
    </main>
  );
}
