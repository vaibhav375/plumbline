import { PageHeader } from "@/components/PageHeader";

import { AuditLog } from "./AuditLog";

export default function AuditPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <PageHeader title="Audit log" subtitle="Every decision and approval, recorded so that nobody can quietly change it later." />
      <AuditLog />
    </main>
  );
}
