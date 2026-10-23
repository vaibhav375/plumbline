import { AppHeader } from "@/components/AppHeader";

import { Queue } from "./Queue";

export default function ReviewPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <AppHeader title="Review queue" subtitle="Submitted content, riskiest first. Private pre-checks never appear here." />
      <Queue />
    </main>
  );
}
