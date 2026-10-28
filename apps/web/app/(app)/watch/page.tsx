import { PageHeader } from "@/components/PageHeader";

import { WatchView } from "./WatchView";

export default function WatchPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader
        title="Claim watch"
        subtitle="Facts change after a post goes live. This shows the live posts whose facts moved, and the live pages that no longer match what was approved."
      />
      <WatchView />
    </main>
  );
}
