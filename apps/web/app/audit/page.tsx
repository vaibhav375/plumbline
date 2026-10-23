import { AppHeader } from "@/components/AppHeader";

import { AuditLog } from "./AuditLog";

export default function AuditPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <AppHeader title="Audit log" subtitle="Every decision, approval and status change, in a tamper-evident chain." />
      <AuditLog />
    </main>
  );
}
