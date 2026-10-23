import { PageHeader } from "@/components/PageHeader";

import { ReviewVersion } from "./ReviewVersion";

export default async function ReviewVersionPage({ params }: { params: Promise<{ versionId: string }> }) {
  const { versionId } = await params;
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader title="Review" subtitle="Agree or disagree with each blocking problem, then approve the post or send it back. Every step is recorded." />
      <ReviewVersion versionId={versionId} />
    </main>
  );
}
