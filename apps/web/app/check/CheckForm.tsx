"use client";

import { useState } from "react";

import { FindingList } from "@/components/FindingList";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { WakingBanner } from "@/components/WakingBanner";
import { check, CheckError, type CheckReport } from "@/lib/api";
import samples from "@/lib/samples.json";

const SAMPLE = samples.find((s) => s.key === "worked-example")!;

export function CheckForm() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [waking, setWaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<CheckReport | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const form = new FormData();
    if (file) form.set("file", file);
    else form.set("text", text);
    form.set("channel", "instagram");
    form.set("region", "IN");
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      setReport(await check(form, setWaking));
    } catch (err) {
      setError(err instanceof CheckError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
      setWaking(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={onSubmit} className="space-y-3">
        <label htmlFor="draft" className="block font-medium">
          Paste a post, or upload a file
        </label>
        <Textarea
          id="draft"
          rows={6}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setFile(null);
          }}
          placeholder="Paste your draft here"
        />
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" onClick={() => (setText(SAMPLE.text), setFile(null))}>
            Load sample post
          </Button>
          <label className="text-sm">
            <span className="sr-only">Upload a file</span>
            <input
              type="file"
              accept=".txt,.md,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <Button type="submit" disabled={busy || (!text.trim() && !file)}>
            {busy ? "Checking…" : "Check"}
          </Button>
        </div>
      </form>
      {waking && <WakingBanner />}
      {error && (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">
          {error}
        </p>
      )}
      {report && <FindingList report={report} />}
    </div>
  );
}
