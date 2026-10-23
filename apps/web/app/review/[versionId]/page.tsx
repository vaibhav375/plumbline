import { AppHeader } from "@/components/AppHeader";

import { ReviewVersion } from "./ReviewVersion";

export default async function ReviewVersionPage({ params }: { params: Promise<{ versionId: string }> }) {
  const { versionId } = await params;
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <AppHeader title="Review" subtitle="Decide each blocking finding, then approve or request changes. Every step is recorded." />
      <ReviewVersion versionId={versionId} />
    </main>
  );
}
