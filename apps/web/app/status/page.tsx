import { AppHeader } from "@/components/AppHeader";
import latest from "@/public/eval/latest.json";

import { CheckerStatus } from "./CheckerStatus";

export default function StatusPage() {
  const evalDate = new Date(latest.generated_at).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  });
  return (
    <main className="mx-auto max-w-3xl space-y-6 p-4 sm:p-6">
      <AppHeader title="Status" subtitle="Is the checker up, which AI providers it can reach, and when it was last evaluated." />
      <CheckerStatus />
      <p className="text-sm">
        Last evaluation run: <strong>{evalDate} IST</strong> on the {latest.dataset.n_items}-post dev set.
      </p>
      <p className="text-xs text-muted-foreground">
        The checker runs on a free tier that sleeps when idle; the first request after a quiet spell takes about 25
        seconds while it wakes. A scheduled ping every 10 minutes keeps that rare.
      </p>
    </main>
  );
}
