import { PageHeader } from "@/components/PageHeader";

import { ConnectView } from "./ConnectView";

export default function ConnectPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader
        title="Connect"
        subtitle="Let your team check posts in chat against your own rulebook, and let publishing tools ask Plumbline before a post goes out."
      />
      <ConnectView />
    </main>
  );
}
